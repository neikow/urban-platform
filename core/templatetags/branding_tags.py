from typing import Any

from django import template
from django.utils.safestring import SafeString

from core.branding import theme_head

register = template.Library()


@register.simple_tag(takes_context=True)
def branding_style(context: dict[str, Any]) -> SafeString | str:
    """The website's fonts, and its colours when they differ from the default theme."""
    return theme_head(context.get("request"))
