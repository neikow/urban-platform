from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationDispatch(models.Model):
    """One row per notification batch already sent, so it is never sent twice.

    Kept outside page models on purpose: page fields are stored in Wagtail
    revisions, and publishing an older revision would bring back a stale
    "not sent yet" flag.
    """

    kind = models.CharField(_("Kind"), max_length=30)
    key = models.CharField(
        _("Key"), max_length=100, help_text=_("What was notified, e.g. project:12")
    )
    created_at = models.DateTimeField(_("Sent At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notification sent")
        verbose_name_plural = _("Notifications sent")
        constraints = [
            models.UniqueConstraint(fields=["kind", "key"], name="unique_notification_dispatch")
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.key}"

    @classmethod
    def claim(cls, kind: str, key: str) -> bool:
        """Record the batch; False when it was already sent (safe under concurrency)."""
        _obj, created = cls.objects.get_or_create(kind=kind, key=key)
        return created
