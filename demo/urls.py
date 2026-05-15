from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"
    ),
    path("google-health/", include("googlehealth.urls")),
    path("sync/", views.sync, name="demo-sync"),
    path("", views.home, name="demo-home"),
]
