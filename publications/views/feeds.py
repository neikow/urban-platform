from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.http import Http404, HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from wagtail.query import PageQuerySet

from core.models import Territory
from publications.ical import calendar
from publications.models import EventPage, PublicationIndexPage, PublicationPage

# Past events stay in the subscribed calendar for a while, then drop off.
CALENDAR_HISTORY = timedelta(days=90)


def _calendar_response(content: str, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def events_ical(request: HttpRequest) -> HttpResponse:
    """Subscribable calendar of published events."""
    events = (
        EventPage.objects.live()
        .public()
        .filter(event_date__gte=timezone.now() - CALENDAR_HISTORY)
        .order_by("event_date")
    )
    name = _("%(site)s — events") % {"site": settings.WEBSITE_NAME}
    return _calendar_response(calendar(events, request, name), "evenements.ics")


def event_ical(request: HttpRequest, event_id: int) -> HttpResponse:
    """A single event, for "add to my calendar"."""
    event = EventPage.objects.live().public().filter(pk=event_id).first()
    if event is None:
        raise Http404
    response = _calendar_response(calendar([event], request, event.title), f"{event.slug}.ics")
    response["Content-Disposition"] = f'attachment; filename="{event.slug}.ics"'
    return response


class PublicationsFeed(Feed):
    """RSS feed of the latest projects and events."""

    def title(self) -> str:
        return _("%(site)s — news") % {"site": settings.WEBSITE_NAME}

    def description(self) -> str:
        area = Territory.current().name_in
        if not area:
            return _("Projects and events.")
        return _("Projects and events %(area)s.") % {"area": area}

    def link(self) -> str:
        index = PublicationIndexPage.objects.live().first()
        return index.url if index and index.url else "/"

    def items(self) -> PageQuerySet:
        return (
            PublicationPage.objects.live().public().order_by("-first_published_at").specific()[:30]
        )

    def item_title(self, item: PublicationPage) -> str:
        return item.title

    def item_description(self, item: PublicationPage) -> str:
        return item.description

    def item_link(self, item: PublicationPage) -> str:
        return item.url or "/"

    def item_pubdate(self, item: PublicationPage) -> datetime | None:
        return item.first_published_at

    def item_updateddate(self, item: PublicationPage) -> datetime | None:
        return item.last_published_at

    def item_categories(self, item: PublicationPage) -> list[str]:
        kind = _("Event") if item.is_event else _("Project")
        category = item.get_category_display() if item.is_project else ""  # type: ignore[attr-defined]
        return [c for c in (str(kind), category) if c]
