from django.urls import include, path

urlpatterns = [
    path("google-health/", include("googlehealth.urls")),
]
