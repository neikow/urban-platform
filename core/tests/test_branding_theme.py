"""The theme overrides: same results as frontend/theme/derive.ts (the control plane's preview)."""

import json

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

from core import branding
from core.models import Branding
from core.tenant import Report, ensure_branding

CASES = json.loads((settings.BASE_DIR / "frontend" / "theme" / "test-cases.json").read_text())[
    "cases"
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_same_overrides_as_the_preview(case):
    assert branding.theme_variables(case["choices"]) == case["variables"]
    assert branding.fonts_used(case["choices"]) == case["fonts"]


def test_every_font_has_its_stylesheet():
    fonts_dir = settings.BASE_DIR / "frontend" / "theme" / "fonts"
    catalog = branding.font_catalog()

    assert {p.stem for p in fonts_dir.glob("*.css")} == set(catalog["fonts"])
    for role, font_id in catalog["defaults"].items():
        assert branding.font(font_id, role)


def save(**fields):
    current = Branding.load()
    for name, value in fields.items():
        setattr(current, name, value)
    current.full_clean()
    current.save()
    return current


@pytest.mark.django_db
class TestBranding:
    def test_unreadable_text_is_refused(self):
        with pytest.raises(ValidationError) as error:
            save(background_color="#ffffff", text_color="#dddddd")
        assert "text_color" in error.value.error_dict

    def test_text_checked_against_the_default_background(self):
        with pytest.raises(ValidationError):
            save(text_color="#fafafa")
        save(background_color="#10151c", text_color="#e8e6e3")

    def test_fonts_from_the_catalog_for_their_role(self):
        save(font_body="inter", font_display="oswald")
        with pytest.raises(ValidationError):
            save(font_body="oswald")  # display only
        with pytest.raises(ValidationError):
            save(font_display="comic-sans")

    def test_pages_link_the_fonts_and_apply_the_overrides(self, client):
        save(background_color="#10151c", text_color="#e8e6e3", font_display="fraunces")

        content = client.get(reverse("register")).content.decode()

        assert "dist/font-jost.css" in content and "dist/font-fraunces.css" in content
        assert "big-shoulders-display.css" not in content
        assert "--color-base-100:#10151c;" in content
        assert '--font-display:"Fraunces Variable", ui-serif, Georgia, serif;' in content

    def test_default_look_links_the_default_fonts(self, client):
        content = client.get(reverse("register")).content.decode()

        assert "dist/font-jost.css" in content
        assert "dist/font-big-shoulders-display.css" in content
        assert ":root,[data-theme" not in content


@pytest.mark.django_db
class TestInitialTheme:
    def test_applied(self):
        report = Report()
        ensure_branding(
            {
                "background_color": "#10151c",
                "text_color": "#e8e6e3",
                "font_body": "inter",
                "font_display": "oswald",
            },
            report,
        )

        current = branding.current()
        assert not report.warnings
        assert (current.background_color, current.text_color) == ("#10151c", "#e8e6e3")
        assert (current.font_body, current.font_display) == ("inter", "oswald")

    def test_unreadable_colours_are_dropped_together(self):
        report = Report()
        ensure_branding({"background_color": "#ffffff", "text_color": "#eeeeee"}, report)

        current = branding.current()
        assert report.warnings and report.done == []
        assert (current.background_color, current.text_color) == ("", "")

    def test_unknown_font_is_reported(self):
        report = Report()
        ensure_branding({"font_body": "comic-sans"}, report)

        assert report.warnings and branding.current().font_body == ""
