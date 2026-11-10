from django.contrib.admin import AdminSite


class PlatformAdminSite(AdminSite):
    def has_permission(self, request):
        user = request.user
        return user.is_active and user.is_superuser