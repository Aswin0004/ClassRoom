
from django.urls import path

from .views import (
    OrganizationListView,
    BranchListCreateView,
)

urlpatterns = [
    path(
        "",
        OrganizationListView.as_view(),
        name="organization-list",
    ),
    path(
        "<slug:org_slug>/branches/",
        BranchListCreateView.as_view(),
        name="branch-list-create",
    ),
]
