"""Minimal iCalendar (RFC 5545) output for events, without a third-party library."""

from collections.abc import Iterable
from datetime import UTC, datetime

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from publications.models import EventPage

CRLF = "\r\n"


def escape_text(value: str) -> str:
    """Escape a TEXT value (RFC 5545 §3.3.11)."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def fold(line: str) -> str:
    """Split a content line into 75-octet chunks, continuation lines starting with a space."""
    encoded = line.encode()
    if len(encoded) <= 75:
        return line
    parts: list[str] = []
    current = b""
    for char in line:
        char_bytes = char.encode()
        limit = 75 if not parts else 74  # continuation lines lose one octet to the space
        if len(current) + len(char_bytes) > limit:
            parts.append(current.decode())
            current = b""
        current += char_bytes
    parts.append(current.decode())
    return (CRLF + " ").join(parts)


def format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def event_lines(event: EventPage, request: HttpRequest) -> list[str]:
    url = request.build_absolute_uri(event.url)
    host = request.get_host().split(":")[0]
    location = ", ".join(
        part for part in (event.location, event.address.replace("\n", ", ")) if part
    )
    if not location and event.is_online and event.online_link:
        location = event.online_link
    description = "\n\n".join(part for part in (event.description, url) if part)

    lines = [
        "BEGIN:VEVENT",
        f"UID:event-{event.pk}@{host}",
        f"DTSTAMP:{format_datetime(event.last_published_at or timezone.now())}",
        f"DTSTART:{format_datetime(event.event_date)}",
    ]
    if event.end_date:
        lines.append(f"DTEND:{format_datetime(event.end_date)}")
    lines += [
        f"SUMMARY:{escape_text(event.title)}",
        f"DESCRIPTION:{escape_text(description)}",
        f"URL:{url}",
    ]
    if location:
        lines.append(f"LOCATION:{escape_text(location)}")
    lines.append("END:VEVENT")
    return lines


def calendar(events: Iterable[EventPage], request: HttpRequest, name: str) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{settings.WEBSITE_NAME}//Events//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(name)}",
        f"X-WR-TIMEZONE:{settings.TIME_ZONE}",
        # Hint for subscribed calendars (Apple, Outlook) to refresh a few times a day.
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for event in events:
        lines += event_lines(event, request)
    lines.append("END:VCALENDAR")
    return CRLF.join(fold(line) for line in lines) + CRLF
