from django.contrib import admin

from .models import GoogleHealthConnection


@admin.register(GoogleHealthConnection)
class GoogleHealthConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "google_user_id",
        "status",
        "connected_at",
        "last_sync_at",
    )
    list_filter = ("status",)
    search_fields = ("customer__username", "google_user_id")
    readonly_fields = ("connected_at",)
