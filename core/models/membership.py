from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class MembershipQuerySet(models.QuerySet["Membership"]):
    def active(self, on: date | None = None) -> "MembershipQuerySet":
        """Memberships running on a day (today by default)."""
        on = on or timezone.localdate()
        return self.filter(starts_on__lte=on).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=on))


class Membership(models.Model):
    """A period during which a user is a member (adhérent).

    A user is a member while one of their memberships runs: participation can be
    reserved to members (Settings › Features). Recorded by administrators until
    members can join from the website; renewals are new memberships.
    """

    user = models.ForeignKey(
        "User", verbose_name=_("Member"), on_delete=models.CASCADE, related_name="memberships"
    )
    starts_on = models.DateField(_("Start"), default=timezone.localdate)
    ends_on = models.DateField(
        _("End"), null=True, blank=True, help_text=_("Leave empty for a membership with no end.")
    )
    note = models.CharField(
        _("Note"), max_length=255, blank=True, help_text=_("E.g. how the membership was paid.")
    )
    created_by = models.ForeignKey(
        "User",
        verbose_name=_("Recorded by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )
    created_at = models.DateTimeField(_("Recorded on"), auto_now_add=True)

    objects = MembershipQuerySet.as_manager()

    class Meta:
        verbose_name = _("Membership")
        verbose_name_plural = _("Memberships")
        ordering = ["-starts_on", "-pk"]

    def __str__(self) -> str:
        end = self.ends_on.isoformat() if self.ends_on else "…"
        return f"{self.user} ({self.starts_on.isoformat()} – {end})"

    def clean(self) -> None:
        super().clean()
        if self.ends_on and self.starts_on and self.ends_on < self.starts_on:
            raise ValidationError({"ends_on": _("The end cannot come before the start.")})

    @property
    def is_active(self) -> bool:
        today = timezone.localdate()
        return self.starts_on <= today and (self.ends_on is None or self.ends_on >= today)

    def as_dict(self) -> dict[str, Any]:
        return {
            "starts_on": self.starts_on.isoformat(),
            "ends_on": self.ends_on.isoformat() if self.ends_on else None,
            "note": self.note,
        }
