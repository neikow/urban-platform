"""The website's name, look and contact, from the Branding setting (core.models).

Each website of the platform sets its own; empty fields fall back to the
defaults (WEBSITE_NAME, the theme in frontend/theme/theme.css).

The theme overrides (colours, fonts) mirror frontend/theme/derive.ts, which the
control plane's preview uses: frontend/theme/test-cases.json checks that both agree.
"""

import json
import re
from functools import cache
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString, mark_safe

if TYPE_CHECKING:
    from core.models import Branding

# The theme's light and dark text colours (base-100 and base-content).
LIGHT_CONTENT = "#fdfbf8"
DARK_CONTENT = "#1b100a"
# Body text on the background: WCAG AA for normal text.
MIN_TEXT_CONTRAST = 4.5
# Cards and borders: the background, shaded toward the text colour.
# In oklab: mixing in oklch loses the hue of near-greys (Chrome), turning them pink.
BASE_200_SHADE = "4%"
BASE_300_SHADE = "9%"
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
FALLBACKS = {
    "sans": "ui-sans-serif, system-ui, sans-serif",
    "serif": "ui-serif, Georgia, serif",
}
THEME_FIELDS = (
    "primary_color",
    "secondary_color",
    "background_color",
    "text_color",
    "font_body",
    "font_display",
)


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


# --- Fonts (frontend/theme/fonts.json) ------------------------------------------------


@cache
def font_catalog() -> dict[str, Any]:
    path = settings.BASE_DIR / "frontend" / "theme" / "fonts.json"
    return dict(json.loads(path.read_text()))


def font(font_id: str, role: str) -> dict[str, Any] | None:
    """The catalog's font ``font_id``, if it may be used for ``role`` (body, display)."""
    entry = font_catalog()["fonts"].get(font_id) if font_id else None
    return entry if entry and role in entry["roles"] else None


def font_choices(role: str) -> list[tuple[str, str]]:
    return [(i, f["label"]) for i, f in font_catalog()["fonts"].items() if role in f["roles"]]


def font_stack(font_id: str, role: str) -> str:
    entry = font(font_id, role)
    return f'"{entry["family"]}", {FALLBACKS[entry["kind"]]}' if entry else ""


def fonts_used(choices: dict[str, str]) -> list[str]:
    """The fonts the website uses (to link their stylesheets), defaults included."""
    defaults = font_catalog()["defaults"]
    used = [
        font_id if font(font_id := choices.get(f"font_{role}", ""), role) else defaults[role]
        for role in ("body", "display")
    ]
    return list(dict.fromkeys(used))


# --- The theme overrides ----------------------------------------------------------------


def _is_color(value: str | None) -> bool:
    return bool(value and HEX_COLOR.match(value))


def theme_variables(choices: dict[str, str]) -> dict[str, str]:
    """The CSS variables replacing the theme's; empty when the defaults are kept."""
    variables = {}
    for name in ("primary", "secondary"):
        color = choices.get(f"{name}_color", "")
        if _is_color(color):
            variables[f"--color-{name}"] = color
            variables[f"--color-{name}-content"] = content_color(color)
    background = choices.get("background_color", "")
    if _is_color(background):
        variables["--color-base-100"] = background
        for level, amount in (("200", BASE_200_SHADE), ("300", BASE_300_SHADE)):
            variables[f"--color-base-{level}"] = (
                f"color-mix(in oklab, var(--color-base-100), var(--color-base-content) {amount})"
            )
    text = choices.get("text_color", "")
    if _is_color(text):
        variables["--color-base-content"] = text
    defaults = font_catalog()["defaults"]
    for role, variable in (("body", "--font-sans"), ("display", "--font-display")):
        font_id = choices.get(f"font_{role}", "")
        if font(font_id, role) and font_id != defaults[role]:
            variables[variable] = font_stack(font_id, role)
    return variables


def theme_choices(request: HttpRequest | None = None) -> dict[str, str]:
    current_branding = current(request)
    return {name: getattr(current_branding, name) for name in THEME_FIELDS}


def theme_css(request: HttpRequest | None = None) -> SafeString | str:
    """The rule overriding the theme, "" when the defaults are kept.

    Same selectors as the daisyUI theme, written after its stylesheet: they win.
    """
    variables = theme_variables(theme_choices(request))
    if not variables:
        return ""
    # Safe: validated colours and the catalog's font names only.
    body = "".join(f"{name}:{value};" for name, value in variables.items())
    return mark_safe(f'<style>:root,[data-theme="light"]{{{body}}}</style>')  # nosec B308 B703


def theme_head(request: HttpRequest | None = None) -> SafeString:
    """In <head>, after the main stylesheet: the fonts' stylesheets, the overrides."""
    choices = theme_choices(request)
    links = format_html_join(
        "\n",
        '<link rel="stylesheet" href="{}">',
        ((static(f"dist/font-{font_id}.css"),) for font_id in fonts_used(choices)),
    )
    return format_html("{}{}", links, theme_css(request))
