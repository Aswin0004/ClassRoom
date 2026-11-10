
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)

from .access import (
    visible_organizations,
    visible_branches,
    is_organization_admin,
)

from .models import Branch

from .serializers import (
    OrganizationSerializer,
    BranchSerializer,
)


class OrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return visible_organizations(self.request.user)


class BranchListCreateView(generics.ListCreateAPIView):
    serializer_class = BranchSerializer

    def get_organization(self):
        if not hasattr(self, "_organization"):
            self._organization = get_object_or_404(
                visible_organizations(self.request.user),
                slug=self.kwargs["org_slug"],
            )

        return self._organization

    def get_queryset(self):
        return visible_branches(
            self.request.user,
            self.get_organization(),
        ).order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = self.get_organization()
        return context

    def perform_create(self, serializer):
        organization = self.get_organization()

        if not is_organization_admin(
            self.request.user, organization
        ):
            raise PermissionDenied(
                "Only organization administrators can create branches."
            )

        try:
            with transaction.atomic():
                serializer.save(organization=organization)

        except IntegrityError:
            raise ValidationError({
                "code": "Branch code already exists."
            })
