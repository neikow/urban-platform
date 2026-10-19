from django.db import models
from django.utils.translation import gettext_lazy as _


class MembershipReminderKind(models.TextChoices):
    EXPIRING = "expiring", _("Membership ending soon")
    GRACE = "grace", _("Membership ended, grace month")
    LAST_CALL = "last_call", _("Grace month ending soon")


class MembershipReminder(models.Model):
    """A renewal reminder sent about a membership, so it is sent once (core.membership_reminders)."""

    membership = models.ForeignKey("Membership", on_delete=models.CASCADE, related_name="reminders")
    kind = models.CharField(max_length=20, choices=MembershipReminderKind.choices)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Membership reminder")
        verbose_name_plural = _("Membership reminders")
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "kind"], name="unique_membership_reminder"
            )
        ]

    def __str__(self) -> str:
        return f"{self.membership} – {self.kind}"
