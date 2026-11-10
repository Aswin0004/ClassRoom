
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import (
    PermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.db import IntegrityError, transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)

from .access import (
    is_organization_admin,
    visible_branches,
    visible_organizations,
)
from .forms import BranchForm, GrantAccessForm
from .models import (
    AuditEvent,
    Branch,
    BranchAssignment,
    Membership,
)
from .services import (
    grant_existing_user_access,
    write_audit,
)


def get_visible_organization(request, slug):
    return get_object_or_404(
        visible_organizations(request.user),
        slug=slug,
    )


def require_organization_admin(request, slug):
    organization = get_visible_organization(
        request, slug
    )

    if not is_organization_admin(
        request.user, organization
    ):
        raise PermissionDenied(
            "You do not have organization management access."
        )

    return organization


@login_required
def workspace_home(request):
    organizations = list(
        visible_organizations(request.user).order_by("name")
    )

    if len(organizations) == 1:
        return redirect(
            "workspace-dashboard",
            org_slug=organizations[0].slug,
        )

    return render(
        request,
        "organizations/workspace_home.html",
        {"organizations": organizations},
    )


@login_required
def workspace_dashboard(request, org_slug):
    organization = get_visible_organization(
        request, org_slug
    )

    is_admin = is_organization_admin(
        request.user, organization
    )

    if is_admin:
        branches = Branch.objects.filter(
            organization=organization
        ).order_by("name")
    else:
        branches = visible_branches(
            request.user, organization
        ).order_by("name")

    context = {
        "organization": organization,
        "is_org_admin": is_admin,
        "branches": branches,
        "branch_count": branches.count(),
        "member_count": (
            Membership.objects.filter(
                organization=organization,
                is_active=True,
            ).values("user_id").distinct().count()
            if is_admin else None
        ),
    }

    return render(
        request,
        "organizations/dashboard.html",
        context,
    )


@login_required
@require_http_methods(["GET", "POST"])
def branch_manage(request, org_slug, branch_id=None):
    organization = require_organization_admin(
        request, org_slug
    )

    if branch_id is None:
        branch = None
    else:
        branch = get_object_or_404(
            Branch,
            pk=branch_id,
            organization=organization,
        )

    if request.method == "POST":
        form = BranchForm(
            request.POST,
            instance=branch,
            organization=organization,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    old_values = None

                    if branch is not None:
                        old_values = {
                            "name": branch.name,
                            "code": branch.code,
                            "is_active": branch.is_active,
                        }

                    saved_branch = form.save(commit=False)
                    saved_branch.organization = organization
                    saved_branch.save()

                    write_audit(
                        organization=organization,
                        actor=request.user,
                        action=(
                            "branch.updated"
                            if branch else "branch.created"
                        ),
                        resource_type="Branch",
                        resource_id=saved_branch.pk,
                        details={
                            "old": old_values,
                            "new": {
                                "name": saved_branch.name,
                                "code": saved_branch.code,
                                "is_active": saved_branch.is_active,
                            },
                        },
                    )

                messages.success(
                    request, "Branch saved successfully."
                )

                return redirect(
                    "workspace-dashboard",
                    org_slug=organization.slug,
                )

            except (IntegrityError, DjangoValidationError):
                form.add_error(
                    None,
                    "Branch could not be saved. "
                    "Check the branch code and try again.",
                )
    else:
        form = BranchForm(
            instance=branch,
            organization=organization,
        )

    return render(
        request,
        "organizations/branch_form.html",
        {
            "organization": organization,
            "is_org_admin": True,
            "form": form,
            "editing": branch is not None,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_directory(request, org_slug):
    organization = require_organization_admin(
        request, org_slug
    )

    if request.method == "POST":
        form = GrantAccessForm(
            request.POST,
            organization=organization,
            actor=request.user,
        )

        if form.is_valid():
            try:
                grant_existing_user_access(
                    organization=organization,
                    actor=request.user,
                    target_user=form.target_user,
                    grant=form.cleaned_data["grant"],
                    branch=form.cleaned_data["branch"],
                )

                messages.success(
                    request,
                    "Access assigned successfully.",
                )

                return redirect(
                    "workspace-members",
                    org_slug=organization.slug,
                )

            except (IntegrityError, DjangoValidationError):
                form.add_error(
                    None,
                    "Could not assign access. Try again.",
                )
    else:
        form = GrantAccessForm(
            organization=organization,
            actor=request.user,
        )

    memberships = Membership.objects.filter(
        organization=organization,
        is_active=True,
    ).select_related("user").order_by(
        "user__username", "role"
    )

    assignments = BranchAssignment.objects.filter(
        branch__organization=organization,
        is_active=True,
    ).select_related(
        "user", "branch"
    ).order_by(
        "branch__name", "user__username"
    )

    return render(
        request,
        "organizations/members.html",
        {
            "organization": organization,
            "is_org_admin": True,
            "form": form,
            "memberships": memberships,
            "assignments": assignments,
        },
    )


@login_required
@require_POST
def revoke_branch_access(
    request,
    org_slug,
    assignment_id,
):
    organization = require_organization_admin(
        request, org_slug
    )

    with transaction.atomic():
        assignment = get_object_or_404(
            BranchAssignment.objects.select_for_update(),
            pk=assignment_id,
            branch__organization=organization,
            is_active=True,
        )

        assignment.is_active = False
        assignment.save(update_fields=["is_active"])

        write_audit(
            organization=organization,
            actor=request.user,
            action="branch_access.revoked",
            resource_type="BranchAssignment",
            resource_id=assignment.pk,
            details={
                "user_id": assignment.user_id,
                "branch_id": assignment.branch_id,
                "role": assignment.role,
            },
        )

    messages.success(
        request,
        "Branch access revoked.",
    )

    return redirect(
        "workspace-members",
        org_slug=organization.slug,
    )
