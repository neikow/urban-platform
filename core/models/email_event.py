import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EmailEventType(models.TextChoices):
    VERIFICATION = "VERIFICATION", _("Email Verification")
    PASSWORD_RESET = "PASSWORD_RESET", _("Password Reset")


class EmailEventStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    SENT = "SENT", _("Sent")
    FAILED = "FAILED", _("Failed")


class EmailEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_events",
        verbose_name=_("User"),
    )
    event_type = models.CharField(
        _("Event Type"),
        max_length=20,
        choices=EmailEventType.choices,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=EmailEventStatus.choices,
        default=EmailEventStatus.PENDING,
    )
    recipient_email = models.EmailField(
        _("Recipient Email"),
        help_text=_("Stored temporarily, cleared on anonymization"),
    )
    sent_at = models.DateTimeField(
        _("Sent At"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
    )
    error_message = models.TextField(
        _("Error Message"),
        blank=True,
    )

    class Meta:
        verbose_name = _("Email Event")
        verbose_name_plural = _("Email Events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} - {self.status} ({self.created_at})"
