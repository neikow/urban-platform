"""The website's name, colours and contact, from the Branding setting (core.models).

Each website of the platform sets its own; empty fields fall back to the
defaults (WEBSITE_NAME, the theme in frontend/src/styles/main.css).
"""

from typing import TYPE_CHECKING

from django.conf import settings
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import SafeString

if TYPE_CHECKING:
    from core.models import Branding

# The theme's light and dark text colours (base-100 and base-content).
LIGHT_CONTENT = "#fdfbf8"
DARK_CONTENT = "#1b100a"


def current(request: HttpRequest | None = None) -> "Branding":
    from core.models import Branding

    return Branding.load(request_or_site=request)


def site_name(request: HttpRequest | None = None) -> str:
    return current(request).site_name or settings.WEBSITE_NAME


def sender_name() -> str:
    """The name the emails come from: DEFAULT_FROM_NAME when set, else the website's."""
    return settings.DEFAULT_FROM_NAME or site_name()


def _luminance(color: str) -> float:
    """WCAG relative luminance of a #rrggbb colour."""

    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# Light text on coloured buttons, like the default theme (3.6:1 on its orange),
# unless it falls under the WCAG ratio for bold text: dark text then.
MIN_LIGHT_CONTRAST = 3


def content_color(background: str) -> str:
    """The text colour on ``background``: the theme's light one if it reads well enough."""
    if contrast(background, LIGHT_CONTENT) >= MIN_LIGHT_CONTRAST:
        return LIGHT_CONTENT
    return DARK_CONTENT


def theme_css(request: HttpRequest | None = None) -> SafeString | str:
    """CSS variables overriding the theme colours, "" when the defaults are kept.

    Same selectors as the daisyUI theme, written after its stylesheet: they win.
    """
    branding = current(request)
    variables = []
    for name, color in (
        ("primary", branding.primary_color),
        ("secondary", branding.secondary_color),
    ):
        if color:
            variables.append(
                f"--color-{name}:{color};--color-{name}-content:{content_color(color)};"
            )
    if not variables:
        return ""
    return format_html('<style>:root,[data-theme="light"]{{{}}}</style>', "".join(variables))
