from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EventInterest(models.Model):
    """A resident flagged an event as interesting.

    Lightweight on purpose: no registration or capacity. It drives the
    "N interested" counter and the reminder sent the day before.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_interests",
        verbose_name=_("User"),
    )
    event = models.ForeignKey(
        "publications.EventPage",
        on_delete=models.CASCADE,
        related_name="interests",
        verbose_name=_("Event"),
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Event interest")
        verbose_name_plural = _("Event interests")
        constraints = [
            models.UniqueConstraint(fields=["user", "event"], name="unique_user_event_interest")
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.event.title}"
