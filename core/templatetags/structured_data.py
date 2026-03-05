import json
from typing import Any

from django import template
from django.conf import settings
from django.http import HttpRequest
from django.utils.safestring import SafeString, mark_safe
from wagtail.images.models import Image, SourceImageIOError
from wagtail.models import Page

register = template.Library()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _absolute_url(request: HttpRequest, path: str) -> str:
    return request.build_absolute_uri(path)


def _image_url(request: HttpRequest, image: Image, spec: str = "fill-1200x630") -> str | None:
    if image is None:
        return None

    try:
        rendition = image.get_rendition(spec)
        return _absolute_url(request, rendition.url)
    except SourceImageIOError:
        return None


def _page_url(request: HttpRequest, page: Page) -> str:
    return _absolute_url(request, page.url)


def _site_name(request: HttpRequest) -> str:
    return settings.WEBSITE_NAME


def _organization(request: HttpRequest) -> dict[str, str]:
    name = _site_name(request)
    return {
        "@type": "Organization",
        "name": name,
        "url": _absolute_url(request, "/"),
    }


# ---------------------------------------------------------------------------
# Per-type schema builders
# ---------------------------------------------------------------------------


def _schema_for_home(request: HttpRequest, page: Page) -> dict[str, Any]:
    site_name = _site_name(request)
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name or page.title,
        "url": _absolute_url(request, "/"),
    }
    if page.search_description:
        data["description"] = page.search_description
    return data


def _schema_for_pedagogy_index(request: HttpRequest, page: Page) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": page.title,
        "url": _page_url(request, page),
        "description": getattr(page, "page_introduction", "") or page.search_description or "",
        "publisher": _organization(request),
    }


def _schema_for_pedagogy_card(request: HttpRequest, page: Page) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": page.title,
        "url": _page_url(request, page),
        "publisher": _organization(request),
    }
    description = getattr(page, "description", "") or page.search_description or ""

    if description:
        data["description"] = description

    image_url = _image_url(request, getattr(page, "hero_image", None))
    if image_url:
        data["image"] = image_url

    if page.first_published_at:
        data["datePublished"] = page.first_published_at.isoformat()
    if page.last_published_at:
        data["dateModified"] = page.last_published_at.isoformat()
    return data


def _schema_for_publication_index(request: HttpRequest, page: Page) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": page.title,
        "url": _page_url(request, page),
        "description": getattr(page, "page_introduction", "") or page.search_description or "",
        "publisher": _organization(request),
    }


def _schema_for_project(request: HttpRequest, page: Page) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "name": page.title,
        "headline": page.title,
        "url": _page_url(request, page),
        "publisher": _organization(request),
    }
    description = getattr(page, "description", "") or page.search_description or ""
    if description:
        data["description"] = description

    image_url = _image_url(request, getattr(page, "hero_image", None))
    if image_url:
        data["image"] = image_url

    category = getattr(page, "get_category_display", None)
    if callable(category):
        cat_label = category()
        if cat_label:
            data["articleSection"] = cat_label

    if page.first_published_at:
        data["datePublished"] = page.first_published_at.isoformat()
    if page.last_published_at:
        data["dateModified"] = page.last_published_at.isoformat()
    return data


def _schema_for_event(request: HttpRequest, page: Page) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": page.title,
        "url": _page_url(request, page),
        "organizer": _organization(request),
    }
    description = getattr(page, "description", "") or page.search_description or ""
    if description:
        data["description"] = description

    image_url = _image_url(request, getattr(page, "hero_image", None))
    if image_url:
        data["image"] = image_url

    event_date = getattr(page, "event_date", None)
    if event_date:
        data["startDate"] = event_date.isoformat()

    end_date = getattr(page, "end_date", None)
    if end_date:
        data["endDate"] = end_date.isoformat()

    is_online = getattr(page, "is_online", False)
    if is_online:
        data["eventAttendanceMode"] = "https://schema.org/OnlineEventAttendanceMode"
        online_link = getattr(page, "online_link", "")
        if online_link:
            data["location"] = {
                "@type": "VirtualLocation",
                "url": online_link,
            }
    else:
        location = getattr(page, "location", "")
        address = getattr(page, "address", "")
        if location or address:
            data["location"] = {
                "@type": "Place",
                "name": location,
                "address": address,
            }
        data["eventAttendanceMode"] = "https://schema.org/OfflineEventAttendanceMode"

    return data


def _schema_fallback(request: HttpRequest, page: Page) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page.title,
        "url": _page_url(request, page),
    }
    if page.search_description:
        data["description"] = page.search_description
    return data


# ---------------------------------------------------------------------------
# Registry: model class name → builder
# ---------------------------------------------------------------------------

_SCHEMA_BUILDERS = {
    "HomePage": _schema_for_home,
    "PedagogyIndexPage": _schema_for_pedagogy_index,
    "PedagogyCardPage": _schema_for_pedagogy_card,
    "PublicationIndexPage": _schema_for_publication_index,
    "ProjectPage": _schema_for_project,
    "EventPage": _schema_for_event,
}


def get_structured_data(request: HttpRequest, page: Page) -> dict[str, Any]:
    """Return the structured data dict for the given page. Public API for testing."""
    class_name = page.__class__.__name__
    builder = _SCHEMA_BUILDERS.get(class_name, _schema_fallback)
    return builder(request, page)


# ---------------------------------------------------------------------------
# Template tag
# ---------------------------------------------------------------------------


@register.simple_tag(takes_context=True)
def structured_data_script(context: Any) -> SafeString:
    """Render a <script type="application/ld+json"> tag for the current page."""
    request: HttpRequest | None = context.get("request")
    page: Page | None = context.get("page")

    if request is None or page is None:
        return mark_safe("")  # nosec B308 B703 — literal empty string, no user input

    schema = get_structured_data(request, page)
    # ensure_ascii=True causes json.dumps to escape <, > and & as \uXXXX,
    # preventing script-injection even if page fields contain those characters.
    json_str = json.dumps(schema, ensure_ascii=True, indent=None)
    return mark_safe(  # nosec B308 B703 — XSS-safe: HTML chars escaped by json.dumps
        f'<script type="application/ld+json">{json_str}</script>'
    )
