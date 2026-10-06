"""Remind interested residents of tomorrow's events."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from core.models import NotificationDispatch
from core.notifications import NotificationKind
from core.notifications.recipients import opted_in
from core.notifications.tasks import absolute_url, notify
from publications.models import EventPage


def events_tomorrow() -> list[EventPage]:
    tomorrow = timezone.localdate() + timedelta(days=1)
    return list(EventPage.objects.live().public().filter(event_date__date=tomorrow))


def send_reminders_for(event: EventPage) -> int:
    if not NotificationDispatch.claim(NotificationKind.EVENT_REMINDER, f"event:{event.pk}"):
        return 0

    start = timezone.localtime(event.event_date)
    where = ", ".join(part for part in (event.location, event.address.replace("\n", ", ")) if part)
    return notify(
        NotificationKind.EVENT_REMINDER,
        opted_in(
            NotificationKind.EVENT_REMINDER, event.interests.values_list("user_id", flat=True)
        ),
        subject=_("Tomorrow: %(title)s") % {"title": event.title},
        template="emails/notifications/event_reminder.html",
        context={
            "event_title": event.title,
            "event_url": absolute_url(event.url or "/"),
            "event_when": f"{date_format(start, 'l j F Y')}, {date_format(start, 'H:i')}",
            "event_where": where,
            "online_link": event.online_link if event.is_online else "",
            "calendar_url": absolute_url(reverse("event_ical", args=[event.pk])),
        },
    )


def send_event_reminders() -> int:
    return sum(send_reminders_for(event) for event in events_tomorrow())
