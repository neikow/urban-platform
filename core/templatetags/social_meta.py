"""Description, canonical URL and Open Graph / Twitter tags for link previews."""

from typing import Any

from django import template
from wagtail.models import Page

from core import branding
from core.templatetags.structured_data import _image_url

register = template.Library()

# Pages that describe a single item are articles; everything else is a website page.
ARTICLE_MODELS = {"projectpage", "eventpage", "pedagogycardpage"}


def page_description(page: Page) -> str:
    specific = page.specific
    return (
        page.search_description
        or getattr(specific, "description", "")
        or getattr(specific, "page_introduction", "")
        or ""
    ).strip()


@register.inclusion_tag("core/components/social_meta.html", takes_context=True)
def social_meta(context: Any) -> dict[str, Any]:
    request = context.get("request")
    if request is None:
        return {}

    page: Page | None = context.get("page")
    site_name = branding.site_name(request)
    data: dict[str, Any] = {
        "site_name": site_name,
        # Query strings (filters, pagination) do not make a different page.
        "canonical_url": request.build_absolute_uri(request.path),
        "title": site_name,
        "description": "",
        "image_url": None,
        "type": "website",
    }

    if isinstance(page, Page):
        specific = page.specific
        data["title"] = page.seo_title or page.title
        data["description"] = page_description(page)
        data["image_url"] = _image_url(request, getattr(specific, "hero_image", None))
        if page.url:
            data["canonical_url"] = request.build_absolute_uri(page.url)
        if specific._meta.model_name in ARTICLE_MODELS:
            data["type"] = "article"

    return data
