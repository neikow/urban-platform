"""Renewal reminders: memberships last a year, with a month of grace after it.

Sent once each per membership, by a daily task, to members who did not renew:

- "expiring": from 16 days before the end;
- "grace": the first week after the end;
- "last_call": the last week of the grace month.

A day missed (the task did not run) is caught up the next day, within the window.
"""

from datetime import date, timedelta
from functools import partial
from typing import Iterator

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone
from django.utils.formats import date_format

from core.models import Membership, MembershipReminder, MembershipReminderKind
from core.models.membership import GRACE_PERIOD

# Days relative to the end of the membership: (first, last) day to send.
WINDOWS = {
    MembershipReminderKind.EXPIRING: (-16, -1),
    MembershipReminderKind.GRACE: (1, 7),
    MembershipReminderKind.LAST_CALL: (GRACE_PERIOD.days - 6, GRACE_PERIOD.days),
}


def not_renewed(memberships: QuerySet[Membership]) -> QuerySet[Membership]:
    """Memberships whose member has no membership running past them."""
    later = Membership.objects.filter(user=OuterRef("user")).filter(
        Q(ends_on__isnull=True) | Q(ends_on__gt=OuterRef("ends_on"))
    )
    return memberships.filter(~Exists(later))


def due_reminders(today: date | None = None) -> Iterator[tuple[Membership, str]]:
    """The reminders to send today, with their kind."""
    today = today or timezone.localdate()
    for kind, (first, last) in WINDOWS.items():
        # first <= today - ends_on <= last
        memberships = (
            not_renewed(
                Membership.objects.filter(
                    ends_on__gte=today - timedelta(days=last),
                    ends_on__lte=today - timedelta(days=first),
                    user__is_active=True,
                )
            )
            .exclude(reminders__kind=kind)
            .select_related("user", "association")
        )
        for membership in memberships:
            yield membership, kind


def send_membership_reminders(today: date | None = None) -> int:
    """Queue today's reminders. Returns how many."""
    from core.emails.tasks import send_membership_email

    sent = 0
    for membership, kind in due_reminders(today):
        try:
            with transaction.atomic():
                MembershipReminder.objects.create(membership=membership, kind=kind)
        except IntegrityError:
            continue  # sent meanwhile by another run
        assert membership.ends_on is not None  # nosec B101: filtered on ends_on
        context = {
            "ends_on": date_format(membership.ends_on, "j F Y"),
            "grace_until": date_format(membership.ends_on + GRACE_PERIOD, "j F Y"),
            "association": membership.association.name if membership.association else None,
        }
        transaction.on_commit(
            partial(send_membership_email.delay, membership.user_id, kind, context)  # type: ignore[attr-defined]  # Celery task
        )
        sent += 1
    return sent
