from typing import Any

from django import template

from core.models import Announcement

register = template.Library()

# Holds the version of the announcement the visitor closed. Set by the
# `data-dismiss-cookie` behaviour (frontend/src/lib/behaviors.ts).
DISMISSED_COOKIE = "announcement_dismissed"


@register.inclusion_tag("core/components/announcement_band.html", takes_context=True)
def announcement_band(context: template.Context) -> dict[str, Any]:
    """The site-wide announcement, unless it is off or this visitor closed it."""
    request = context.get("request")
    if request is None:
        return {}
    announcement = Announcement.load(request_or_site=request)
    if not announcement.is_active:
        return {}
    if request.COOKIES.get(DISMISSED_COOKIE) == announcement.version:
        return {}
    return {
        "announcement": announcement,
        "dismiss_cookie": f"{DISMISSED_COOKIE}={announcement.version}",
    }
