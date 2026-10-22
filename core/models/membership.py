from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# A membership keeps its rights this long after it ends, time to renew it.
GRACE_PERIOD = timedelta(days=31)
# A member may renew this long before their membership ends.
RENEWAL_OPENS = timedelta(days=31)


class MembershipQuerySet(models.QuerySet["Membership"]):
    def active(self, on: date | None = None, grace: bool = False) -> "MembershipQuerySet":
        """Memberships running on a day (today by default), or ended in the grace period."""
        on = on or timezone.localdate()
        until = on - GRACE_PERIOD if grace else on
        return self.filter(starts_on__lte=on).filter(
            Q(ends_on__isnull=True) | Q(ends_on__gte=until)
        )


def one_year_from(starts: date) -> date:
    """The last day of a year-long membership starting on ``starts``."""
    try:
        anniversary = starts.replace(year=starts.year + 1)
    except ValueError:  # February 29
        anniversary = starts.replace(year=starts.year + 1, day=28) + timedelta(days=1)
    return anniversary - timedelta(days=1)


def membership_period(
    memberships: MembershipQuerySet, today: date | None = None
) -> tuple[date, date]:
    """The days a membership paid today covers: one year, whenever it is paid.

    It starts today or, when renewing, the day after the last membership ends.
    """
    today = today or timezone.localdate()
    last_end = (
        memberships.filter(ends_on__gte=today)
        .order_by("-ends_on")
        .values_list("ends_on", flat=True)
        .first()
    )
    starts = last_end + timedelta(days=1) if last_end else today
    return starts, one_year_from(starts)


def may_join(memberships: MembershipQuerySet, today: date | None = None) -> bool:
    """Whether paying makes sense today: not a member, or less than a month before the end."""
    today = today or timezone.localdate()
    if memberships.active(today).filter(ends_on__isnull=True).exists():
        return False
    last_end = (
        memberships.filter(ends_on__gte=today)
        .order_by("-ends_on")
        .values_list("ends_on", flat=True)
        .first()
    )
    return last_end is None or today >= last_end - RENEWAL_OPENS


class Membership(models.Model):
    """A period during which a user is a member (adhérent).

    A user is a member while one of their memberships runs: participation can be
    reserved to members (Settings › Features). Recorded by administrators until
    members can join from the website; renewals are new memberships.
    """

    user = models.ForeignKey(
        "User", verbose_name=_("Member"), on_delete=models.CASCADE, related_name="memberships"
    )
    association = models.ForeignKey(
        "NeighborhoodAssociation",
        verbose_name=_("Neighborhood Association"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
        help_text=_("The association (CIQ) the member joins with this membership."),
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
            "association": self.association.name if self.association else None,
        }
