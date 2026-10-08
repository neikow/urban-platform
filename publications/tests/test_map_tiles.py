from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from publications import map_tiles
from publications.geo import map_config
from publications.map_tiles import TilesError, is_due, refresh_tiles, tiles_url
from publications.models import MapSettings
from publications.tasks import refresh_map_tiles


@pytest.fixture
def media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def fake_extract(monkeypatch):
    """Replace the download: write a small file, remember the builds asked for."""
    builds = []

    def extract(build: str, output: Path) -> None:
        builds.append(build)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"tiles")

    monkeypatch.setattr(map_tiles, "extract", extract)
    return builds


def latest(build: str):
    return patch.object(map_tiles, "latest_build", return_value=build)


def update_settings(**fields):
    map_settings = MapSettings.load()
    MapSettings.objects.filter(pk=map_settings.pk).update(**fields)
    return MapSettings.load()


@pytest.mark.django_db
class TestTilesUrl:
    def test_falls_back_to_the_static_tiles(self, media):
        assert tiles_url().startswith("/static/")
        assert map_config()["tilesUrl"] == tiles_url()

    def test_uses_the_updated_tiles(self, media):
        (media / "map-tiles").mkdir()
        (media / "map-tiles" / "local-area-20261001.pmtiles").write_bytes(b"tiles")
        update_settings(tiles_file="map-tiles/local-area-20261001.pmtiles")

        assert tiles_url() == "/media/map-tiles/local-area-20261001.pmtiles"

    def test_ignores_a_missing_file(self, media):
        update_settings(tiles_file="map-tiles/gone.pmtiles")

        assert tiles_url().startswith("/static/")


@pytest.mark.django_db
class TestIsDue:
    def test_defaults(self):
        map_settings = MapSettings.load()

        assert map_settings.tiles_auto_update
        assert map_settings.tiles_update_interval_days == 30

    def test_after_the_interval(self):
        now = timezone.now()
        map_settings = update_settings(tiles_checked_at=now - timedelta(days=30))

        assert is_due(map_settings, now)
        assert not is_due(map_settings, now - timedelta(days=1))

    def test_never_when_disabled(self):
        map_settings = update_settings(tiles_auto_update=False, tiles_checked_at=None)

        assert not is_due(map_settings, timezone.now())

    def test_first_check_counts_from_the_shipped_tiles(self, tmp_path, monkeypatch):
        shipped = tmp_path / "local-area.pmtiles"
        shipped.write_bytes(b"tiles")
        monkeypatch.setattr(map_tiles, "static_tiles_path", lambda: shipped)
        map_settings = MapSettings.load()
        now = timezone.now()

        assert not is_due(map_settings, now)
        assert is_due(map_settings, now + timedelta(days=31))


@pytest.mark.django_db
class TestRefresh:
    def test_downloads_records_and_prunes(self, media, fake_extract):
        with latest("20261001.pmtiles"):
            first = refresh_tiles(force=True)
        with latest("20261008.pmtiles"):
            second = refresh_tiles(force=True)
        with latest("20261015.pmtiles"):
            third = refresh_tiles(force=True)

        assert third == "map-tiles/local-area-20261015.pmtiles"
        map_settings = MapSettings.load()
        assert map_settings.tiles_build == "20261015.pmtiles"
        assert map_settings.tiles_file == third
        assert map_settings.tiles_updated_at is not None
        assert map_settings.tiles_error == ""
        # The previous file stays for pages cached with its URL; older ones go.
        files = sorted(p.name for p in (media / "map-tiles").iterdir())
        assert files == [Path(second).name, Path(third).name]
        assert first not in files

    def test_same_build_is_not_downloaded_again(self, media, fake_extract):
        with latest("20261001.pmtiles"):
            refresh_tiles(force=True)
        update_settings(tiles_checked_at=timezone.now() - timedelta(days=60))

        with latest("20261001.pmtiles"):
            assert refresh_tiles() is None

        assert fake_extract == ["20261001.pmtiles"]
        assert MapSettings.load().tiles_checked_at > timezone.now() - timedelta(minutes=1)

    def test_not_due_does_nothing(self, media, fake_extract):
        update_settings(tiles_checked_at=timezone.now())

        with latest("20261001.pmtiles") as listed:
            assert refresh_tiles() is None

        listed.assert_not_called()
        assert fake_extract == []

    def test_failure_is_recorded(self, media, monkeypatch):
        def fail(build, output):
            raise TilesError("pmtiles extract failed: boom")

        monkeypatch.setattr(map_tiles, "extract", fail)

        with latest("20261001.pmtiles"):
            assert refresh_tiles(force=True) is None

        map_settings = MapSettings.load()
        assert map_settings.tiles_error == "pmtiles extract failed: boom"
        assert map_settings.tiles_checked_at is not None
        assert map_settings.tiles_file == ""

    def test_task(self, media, fake_extract):
        with latest("20261001.pmtiles"):
            assert (
                refresh_map_tiles.delay(force=True).get() == "map-tiles/local-area-20261001.pmtiles"
            )

    def test_command_refresh(self, media, fake_extract):
        with latest("20261001.pmtiles"):
            call_command("build_map_tiles", "--refresh")

        assert MapSettings.load().tiles_build == "20261001.pmtiles"

    def test_command_refresh_failure(self, media):
        with patch.object(map_tiles, "latest_build", side_effect=TilesError("offline")):
            with pytest.raises(CommandError):
                call_command("build_map_tiles", "--refresh")


@pytest.mark.django_db
class TestManualRefresh:
    @pytest.fixture
    def editor(self, client):
        from core.models import User

        client.force_login(User.objects.create_superuser(email="super@example.com", password="x"))
        return client

    def test_settings_page_offers_the_button(self, editor):
        url = reverse("wagtailsettings:edit", args=["publications", "mapsettings"])

        content = editor.get(url, follow=True).content.decode()

        assert f'formaction="{reverse("map_tiles_refresh")}"' in content

    def test_button_runs_a_forced_refresh(self, editor, media, fake_extract):
        update_settings(tiles_checked_at=timezone.now())

        with latest("20261001.pmtiles"):
            response = editor.post(reverse("map_tiles_refresh"))

        assert response.status_code == 302
        assert fake_extract == ["20261001.pmtiles"]
        assert MapSettings.load().tiles_build == "20261001.pmtiles"

    def test_no_second_refresh_while_one_runs(self, editor, fake_extract):
        with patch.object(map_tiles, "is_refreshing", return_value=True):
            editor.post(reverse("map_tiles_refresh"))

        assert fake_extract == []

    def test_needs_the_settings_permission(self, client, fake_extract):
        from core.models import User, UserRole

        member = User.objects.create_user(
            email="member@example.com", password="x", role=UserRole.ASSOCIATION_MEMBER
        )
        client.force_login(member)

        response = client.post(reverse("map_tiles_refresh"))

        assert response.status_code in (302, 403)
        assert fake_extract == []

    def test_get_is_refused(self, editor):
        assert editor.get(reverse("map_tiles_refresh")).status_code == 405
