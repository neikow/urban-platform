import io
import json
from unittest.mock import patch

import pytest
from django.core.management import call_command
from wagtail.models import Site

from about.models import AboutCommissionPage, AboutWebsitePage
from core import branding, territories
from core.models import Territory, User, UserRole
from core.tenant import Report, TenantConfig, bootstrap
from home.models import HomePage

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.4, 43.5], [5.5, 43.5], [5.5, 43.6], [5.4, 43.6], [5.4, 43.5]]],
}
AIX = territories.from_feature(
    {
        "type": "Feature",
        "properties": {"nom": "Aix-en-Provence", "code": "13001", "codesPostaux": ["13100"]},
        "geometry": SQUARE,
    }
)

CONFIG = TenantConfig(
    base_url="https://aix.example.org",
    admin_email="admin@aix.example.org",
    territory="13001",
    contact_email="bonjour@aix.example.org",
)


@pytest.fixture
def services():
    """The outside world: geo.api.gouv.fr, the admin invitation, the map tiles."""
    with (
        patch("core.territories.fetch", return_value=AIX) as fetch,
        patch("core.emails.tasks.send_invitation_email.delay") as invite,
        patch("publications.map_tiles.queue_refresh") as tiles,
    ):
        yield {"fetch": fetch, "invite": invite, "tiles": tiles}


def run(config=CONFIG, capture=None) -> Report:
    if capture is None:
        return bootstrap(config)
    with capture(execute=True):
        return bootstrap(config)


class TestConfig:
    def test_from_environment(self):
        config = TenantConfig.from_environment(
            {
                "BASE_URL": " https://aix.example.org ",
                "TENANT_ADMIN_EMAIL": "Admin@Aix.example.org",
                "TENANT_TERRITORY": "13001",
            }
        )

        assert config.base_url == "https://aix.example.org"
        assert config.admin_email == "admin@aix.example.org"
        assert config.territory == "13001"
        assert config.contact_email == ""


@pytest.mark.django_db
class TestFirstRun:
    def test_sets_everything_up(self, services, django_capture_on_commit_callbacks):
        report = run(capture=django_capture_on_commit_callbacks)

        assert not report.warnings
        site = Site.objects.get(is_default_site=True)
        assert (site.hostname, site.port) == ("aix.example.org", 443)

        admin = User.objects.get(email="admin@aix.example.org")
        assert admin.role == UserRole.ADMIN
        assert admin.is_superuser and admin.is_verified
        assert not admin.has_usable_password()
        services["invite"].assert_called_once_with(admin.pk)

        assert Territory.current().code == "13001"
        services["tiles"].assert_called_once()
        assert branding.current().contact_email == "bonjour@aix.example.org"

    def test_starter_pages_name_the_website(self, services, settings):
        settings.WEBSITE_NAME = "Aix Ensemble"
        run()

        home = HomePage.objects.get()
        assert home.live and not home.has_unpublished_changes
        content = json.dumps(list(home.content.raw_data), ensure_ascii=False)
        assert "Aix Ensemble" in content
        assert "à Aix-en-Provence" in content
        assert "bonjour@aix.example.org" in content

        association = AboutCommissionPage.objects.get()
        assert (association.title, association.slug) == ("L'association", "association")
        assert AboutWebsitePage.objects.get().content

    def test_runs_without_any_variable(self):
        report = bootstrap(TenantConfig())

        assert not report.warnings
        assert not User.objects.exists()


@pytest.mark.django_db
class TestNextRuns:
    def test_nothing_to_do(self, services):
        run()
        services["fetch"].reset_mock()

        report = run()

        assert report.done == []
        services["fetch"].assert_not_called()

    def test_keeps_what_the_association_changed(self, services):
        run()
        current = branding.current()
        current.contact_email = "autre@example.org"
        current.save()
        home = HomePage.objects.get()
        home.content = json.dumps([])
        home.save_revision()  # an unpublished draft: the editor is at work

        run()

        assert branding.current().contact_email == "autre@example.org"
        home = HomePage.objects.get()
        assert home.has_unpublished_changes
        assert not home.get_latest_revision_as_object().content

    def test_never_touches_an_existing_account(self, services):
        User.objects.create_user(email="admin@aix.example.org", password="x", role=UserRole.CITIZEN)

        run()

        assert User.objects.get(email="admin@aix.example.org").role == UserRole.CITIZEN
        services["invite"].assert_not_called()

    def test_moves_to_a_new_territory(self, services, territory):
        assert territory.code == "13207"

        run()

        assert Territory.current().code == "13001"

    def test_territory_service_down_is_retried(self, services):
        services["fetch"].side_effect = territories.TerritoryUnavailable("down")

        report = run()

        assert report.warnings and "13001" in report.warnings[0]
        assert Territory.current().code == ""
        # The rest still ran.
        assert User.objects.filter(email="admin@aix.example.org").exists()


@pytest.mark.django_db
class TestCommand:
    def test_reads_the_environment(self, services, monkeypatch):
        monkeypatch.setenv("BASE_URL", "http://localhost:8000")
        monkeypatch.setenv("TENANT_ADMIN_EMAIL", "admin@example.org")
        out = io.StringIO()

        call_command("bootstrap_tenant", stdout=out, stderr=io.StringIO())

        assert "admin@example.org" in out.getvalue()
        assert Site.objects.get(is_default_site=True).port == 8000
