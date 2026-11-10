
from django.db import transaction

from .models import (
    AuditEvent,
    BranchAssignment,
    Membership,
)
from django.core.exceptions import PermissionDenied
from .access import is_organization_admin

GRANT_MAPPING = {
    "ADMIN": (
        Membership.Role.ADMIN,
        None,
    ),
    "STAFF": (
        Membership.Role.STAFF,
        None,
    ),
    "MANAGER": (
        Membership.Role.STAFF,
        BranchAssignment.Role.MANAGER,
    ),
    "TRAINER": (
        Membership.Role.TRAINER,
        BranchAssignment.Role.TRAINER,
    ),
    "STUDENT": (
        Membership.Role.STUDENT,
        BranchAssignment.Role.STUDENT,
    ),
}


def write_audit(
    *,
    organization,
    actor,
    action,
    resource_type,
    resource_id,
    details=None,
):
    return AuditEvent.objects.create(
        organization=organization,
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
    )


@transaction.atomic
def grant_existing_user_access(
    *,
    organization,
    actor,
    target_user,
    grant,
    branch=None,
):
    if not is_organization_admin(actor, organization):
        raise PermissionDenied(
            "Organization admin access is required."
        )

    if not target_user.is_active:
        raise PermissionDenied("Target account is inactive.")

    if grant not in GRANT_MAPPING:
        raise ValueError("Unsupported access grant.")

    if grant == "ADMIN":
        is_owner = Membership.objects.filter(
            organization=organization,
            user=actor,
            role=Membership.Role.OWNER,
            is_active=True,
        ).exists()

        if not is_owner:
            raise PermissionDenied(
                "Only owners can grant organization admin access."
            )
    org_role, branch_role = GRANT_MAPPING[grant]
    if branch_role is None and branch is not None:
        raise ValueError(
            "Organization-wide grants cannot target a branch."
        )
    membership, created = Membership.objects.get_or_create(
        organization=organization,
        user=target_user,
        role=org_role,
        defaults={"is_active": True},
    )

    if not membership.is_active:
        membership.is_active = True
        membership.save(update_fields=["is_active"])

    assignment = None

    if branch_role:
        if (
            branch is None
            or branch.organization_id != organization.pk
            or not branch.is_active
        ):
            raise ValueError("Invalid branch for access grant.")

        assignment, assignment_created = (
            BranchAssignment.objects.get_or_create(
                branch=branch,
                user=target_user,
                role=branch_role,
                defaults={"is_active": True},
            )
        )

        if not assignment.is_active:
            assignment.is_active = True
            assignment.save(update_fields=["is_active"])

    write_audit(
        organization=organization,
        actor=actor,
        action="access.granted",
        resource_type="User",
        resource_id=target_user.pk,
        details={
            "grant": grant,
            "branch_id": branch.pk if branch else None,
        },
    )

    return membership, assignment
