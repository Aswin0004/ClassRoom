from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import (
    Organization,
    Branch,
    Membership,
    BranchAssignment,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name", "slug")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "organization",
        "city",
        "is_active",
    )
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "role",
        "is_active",
    )
    list_filter = ("organization", "role", "is_active")


@admin.register(BranchAssignment)
class BranchAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "branch",
        "role",
        "is_active",
    )
    list_filter = ("role", "is_active")