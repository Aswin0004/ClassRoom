
from django.urls import path

from . import workspace_views as views


urlpatterns = [
    path(
        "",
        views.workspace_home,
        name="workspace-home",
    ),

    path(
        "<slug:org_slug>/",
        views.workspace_dashboard,
        name="workspace-dashboard",
    ),

    path(
        "<slug:org_slug>/branches/new/",
        views.branch_manage,
        name="workspace-branch-create",
    ),

    path(
        "<slug:org_slug>/branches/<int:branch_id>/edit/",
        views.branch_manage,
        name="workspace-branch-edit",
    ),

    path(
        "<slug:org_slug>/members/",
        views.member_directory,
        name="workspace-members",
    ),

    path(
        "<slug:org_slug>/assignments/<int:assignment_id>/revoke/",
        views.revoke_branch_access,
        name="workspace-assignment-revoke",
    ),
]
