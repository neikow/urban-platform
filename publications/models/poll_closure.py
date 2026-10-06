from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PollClosureReason(models.TextChoices):
    END_DATE = "END_DATE", _("End date reached")
    MANUAL = "MANUAL", _("Closed by an editor")


class PollClosure(models.Model):
    """A project's poll is closed for good.

    Not a page field: those are restored from Wagtail revisions, so
    publishing an older draft would silently reopen the poll.
    """

    project = models.OneToOneField(
        "publications.ProjectPage",
        on_delete=models.CASCADE,
        related_name="poll_closure",
        verbose_name=_("Project"),
    )
    closed_at = models.DateTimeField(_("Closed at"), auto_now_add=True)
    reason = models.CharField(_("Reason"), max_length=20, choices=PollClosureReason.choices)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Closed by"),
    )

    class Meta:
        verbose_name = _("Poll closure")
        verbose_name_plural = _("Poll closures")

    def __str__(self) -> str:
        return f"{self.project} ({self.get_reason_display()})"
