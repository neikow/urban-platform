from datetime import timedelta
from unittest import mock

import pytest
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import User
from home.models import HomePage
from publications.event_reminders import send_event_reminders
from publications.models import EventInterest, EventPage, PublicationIndexPage


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
    return index


def event_in(index, days, slug) -> EventPage:
    start = (timezone.localtime() + timedelta(days=days)).replace(hour=18, minute=30)
    event = EventPage(
        title=slug.title(), slug=slug, event_date=start, location="Place Saint-Eugène"
    )
    index.add_child(instance=event)
    event.save_revision().publish()
    return event


def interested(event, email, **prefs) -> User:
    user = User.objects.create_user(
        email=email, password="x", first_name="I", last_name="J", is_verified=True, **prefs
    )
    EventInterest.objects.create(user=user, event=event)
    return user


@pytest.fixture
def queued():
    with mock.patch("core.notifications.tasks.send_notification_email") as task:
        yield task.delay


@pytest.mark.django_db
def test_reminds_opted_in_people_of_tomorrows_events_once(index, queued):
    tomorrow = event_in(index, 1, "demain")
    later = event_in(index, 3, "plus-tard")
    wants = interested(tomorrow, "wants@example.com", notify_event_reminders=True)
    interested(tomorrow, "silent@example.com")
    interested(later, "later@example.com", notify_event_reminders=True)

    send_event_reminders()
    send_event_reminders()  # the daily task running twice sends nothing new

    assert queued.call_count == 1
    user_id, kind, subject, template, context = queued.call_args.args
    assert (user_id, kind) == (wants.pk, "event_reminder")
    assert context["event_where"] == "Place Saint-Eugène"
    assert "18:30" in context["event_when"]
    assert context["calendar_url"].endswith(f"/evenements/{tomorrow.pk}/agenda.ics")


@pytest.mark.django_db
def test_unpublished_events_are_skipped(index, queued):
    event = event_in(index, 1, "demain")
    interested(event, "wants@example.com", notify_event_reminders=True)
    event.unpublish()

    send_event_reminders()

    queued.assert_not_called()


def test_reminder_email_renders():
    html = render_to_string(
        "emails/notifications/event_reminder.html",
        {
            "user": User(first_name="Nora"),
            "event_title": "Fête du quartier",
            "event_url": "https://example.com/fete/",
            "event_when": "samedi 10 octobre 2026, 18:30",
            "event_where": "Place Saint-Eugène",
            "online_link": "",
            "calendar_url": "https://example.com/fete.ics",
            "unsubscribe_url": "https://example.com/u/",
        },
    )

    assert "Fête du quartier" in html
    assert "Place Saint-Eugène" in html
