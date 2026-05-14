from django.conf import settings
from django.db import models


class ConnectionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISCONNECTED = "disconnected", "Disconnected"
    REVOKED = "revoked", "Revoked"


class GoogleHealthConnection(models.Model):
    """Per-user OAuth state for the Google Health API.

    Health records persist through django-healthdatamodel; this model only
    holds the credentials needed to fetch them.
    """

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_health_connection",
    )
    google_user_id = models.CharField(max_length=128, db_index=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()
    scopes = models.JSONField(default=list)
    status = models.CharField(
        max_length=32,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.ACTIVE,
    )
    connected_at = models.DateTimeField(auto_now_add=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Google Health connection"
        verbose_name_plural = "Google Health connections"

    def __str__(self) -> str:
        return (
            f"GoogleHealthConnection(customer={self.customer_id}, status={self.status})"
        )
