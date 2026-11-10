
from .models import (
    Organization,
    Branch,
    Membership,
    BranchAssignment,
)


ADMIN_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
]


def visible_organizations(user):
    if not user.is_authenticated or not user.is_active:
        return Organization.objects.none()

    return Organization.objects.filter(
        is_active=True,
        memberships__user=user,
        memberships__is_active=True,
    ).distinct()


def is_organization_admin(user, organization):
    if not user.is_authenticated or not user.is_active:
        return False

    return Membership.objects.filter(
        user=user,
        organization=organization,
        organization__is_active=True,
        role__in=ADMIN_ROLES,
        is_active=True,
    ).exists()


def visible_branches(user, organization):
    queryset = Branch.objects.filter(
        organization=organization,
        organization__is_active=True,
        is_active=True,
    )

    if not user.is_authenticated or not user.is_active:
        return queryset.none()

    active_roles = set(
        Membership.objects.filter(
            organization=organization,
            user=user,
            is_active=True,
        ).values_list("role", flat=True)
    )

    if not active_roles:
        return queryset.none()

    if active_roles.intersection({
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }):
        return queryset

    allowed_assignments = []

    if Membership.Role.STAFF in active_roles:
        allowed_assignments.append(
            BranchAssignment.Role.MANAGER
        )

    if Membership.Role.TRAINER in active_roles:
        allowed_assignments.append(
            BranchAssignment.Role.TRAINER
        )

    if Membership.Role.STUDENT in active_roles:
        allowed_assignments.append(
            BranchAssignment.Role.STUDENT
        )

    return queryset.filter(
        assignments__user=user,
        assignments__is_active=True,
        assignments__role__in=allowed_assignments,
    ).distinct()