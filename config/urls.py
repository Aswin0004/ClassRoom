
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import include, path

from config import health


@login_required
def home(request):
    return redirect("workspace-home")


urlpatterns = [
    path("", home, name="home"),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path("admin/", admin.site.urls),

    path(
        "workspace/",
        include("organizations.workspace_urls"),
    ),

    path(
        "api/v1/organizations/",
        include("organizations.urls"),
    ),

    path(
        "health/live/",
        health.live,
        name="health-live",
    ),

    path(
        "health/ready/",
        health.ready,
        name="health-ready",
    ),
]
