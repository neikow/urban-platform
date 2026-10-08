import pytest
from django.urls import reverse

from core import branding
from core.branding import DARK_CONTENT, LIGHT_CONTENT, content_color, contrast, theme_css
from core.models import Branding
from core.page_templates import placeholders
from core.tests.utils.factories import ImageFactory
from home.page_templates import TEMPLATES


def set_branding(**fields):
    current = Branding.load()
    for name, value in fields.items():
        setattr(current, name, value)
    current.save()
    return current


@pytest.fixture
def media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


class TestColors:
    def test_contrast_ratio(self):
        assert contrast("#000000", "#ffffff") == pytest.approx(21)
        assert contrast("#777777", "#777777") == pytest.approx(1)

    @pytest.mark.parametrize(
        ("background", "expected"),
        [
            ("#003d82", LIGHT_CONTENT),
            ("#e94f37", LIGHT_CONTENT),  # the default orange, as in the theme
            ("#f5d90a", DARK_CONTENT),
            ("#9fd3f0", DARK_CONTENT),
        ],
    )
    def test_content_reads_best(self, background, expected):
        assert content_color(background) == expected


@pytest.mark.django_db
class TestSettings:
    def test_defaults(self, settings):
        settings.DEFAULT_FROM_NAME = ""

        assert branding.site_name() == settings.WEBSITE_NAME
        assert branding.sender_name() == settings.WEBSITE_NAME
        assert theme_css() == ""

    def test_name_from_the_admin(self, settings):
        settings.DEFAULT_FROM_NAME = ""
        set_branding(site_name="Quartiers Vivants")

        assert branding.site_name() == "Quartiers Vivants"
        assert branding.sender_name() == "Quartiers Vivants"

    def test_sender_name_from_the_environment_wins(self, settings):
        settings.DEFAULT_FROM_NAME = "Équipe"
        set_branding(site_name="Quartiers Vivants")

        assert branding.sender_name() == "Équipe"

    def test_colours(self):
        set_branding(primary_color="#003d82")
        css = str(theme_css())

        assert "--color-primary:#003d82;" in css
        assert f"--color-primary-content:{LIGHT_CONTENT};" in css
        assert "--color-secondary" not in css

    def test_rejects_what_is_not_a_colour(self):
        from django.core.exceptions import ValidationError

        current = Branding.load()
        current.primary_color = "red;}body{display:none"
        with pytest.raises(ValidationError):
            current.full_clean()


@pytest.mark.django_db
class TestPages:
    def test_default_look(self, client):
        content = client.get(reverse("register")).content.decode()

        assert "images/favicon.svg" in content
        assert "--color-primary" not in content

    def test_name_colours_logo_and_contact(self, client, media):
        set_branding(
            site_name="Quartiers Vivants",
            tagline="Ensemble, dans nos rues",
            contact_email="bonjour@example.org",
            primary_color="#003d82",
            logo=ImageFactory(),
        )

        content = client.get(reverse("register")).content.decode()

        assert "- Quartiers Vivants" in content
        assert "--color-primary:#003d82;" in content
        assert "images/favicon.svg" not in content
        assert ".png" in content  # the favicon, from the logo
        assert "Ensemble, dans nos rues" in content
        assert "mailto:bonjour@example.org" in content

    def test_signup_without_photo(self, client):
        response = client.get(reverse("register"))

        assert response.status_code == 200
        assert "endoume" not in response.content.decode()

    def test_signup_photo(self, client, media):
        photo = ImageFactory(title="Le quartier")
        set_branding(signup_image=photo)

        content = client.get(reverse("register")).content.decode()

        assert photo.get_rendition("fill-1200x1600").url in content
        assert "bg-secondary" not in content


@pytest.mark.django_db
class TestStarterContent:
    def test_placeholders_name_the_website(self, territory):
        set_branding(site_name="Quartiers Vivants", contact_email="bonjour@example.org")
        values = placeholders()

        assert values["{site_name}"] == "Quartiers Vivants"
        assert values["{area_in}"] == territory.name_in
        assert 'href="mailto:bonjour@example.org"' in values["{contact}"]

    def test_left_for_the_editor_without_contact(self):
        assert placeholders()["{contact}"] == "[adresse de contact]"

    @pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.slug)
    def test_home_templates_are_filled(self, template, territory):
        set_branding(site_name="Quartiers Vivants")
        content = str(template.content())

        assert "{site_name}" not in content
        assert "{area_in}" not in content
        assert "{contact}" not in content
        assert "Marseille" not in content.replace(territory.name_in, "")
        assert "CIQ" not in content
