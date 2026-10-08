import io
import json
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse

from core import geocoding, territories
from core.models import Territory
from core.territories import TerritoryUnavailable, from_feature

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.4, 43.5], [5.5, 43.5], [5.5, 43.6], [5.4, 43.6], [5.4, 43.5]]],
}
AIX = {
    "type": "Feature",
    "properties": {"nom": "Aix-en-Provence", "code": "13001", "codesPostaux": ["13100", "13090"]},
    "geometry": SQUARE,
}
LYON_1 = {
    "type": "Feature",
    "properties": {
        "nom": "Lyon 1er Arrondissement",
        "code": "69381",
        "codesPostaux": ["69001"],
        "codeParent": "69123",
    },
    "geometry": SQUARE,
}


def api(*payloads):
    """Stand-in for urlopen: the given answers, in order."""
    return patch(
        "core.territories.urlopen",
        side_effect=[io.BytesIO(json.dumps(p).encode()) for p in payloads],
    )


class TestFromFeature:
    def test_commune(self):
        data = from_feature(AIX)

        assert data.name == "Aix-en-Provence"
        assert data.name_in == "à Aix-en-Provence"
        assert (data.city_name, data.city_code) == ("Aix-en-Provence", "13001")
        assert data.postal_codes == ["13090", "13100"]
        assert data.boundary == SQUARE

    def test_arrondissement_is_searched_in_its_city(self):
        data = from_feature(LYON_1)

        assert data.name == "1er arrondissement de Lyon"
        assert data.name_in == "dans le 1er arrondissement de Lyon"
        assert (data.city_name, data.city_code) == ("Lyon", "69123")

    def test_bundled_marseille_7e(self):
        data = territories.from_file(territories.MARSEILLE_7E)

        assert data.name == "7e arrondissement de Marseille"
        assert (data.city_name, data.city_code) == ("Marseille", "13055")
        assert data.postal_codes == ["13007"]
        assert data.boundary["type"] == "MultiPolygon"

    @pytest.mark.parametrize(
        "feature",
        [
            {},
            {"properties": {"nom": "X", "code": "1"}},
            {**AIX, "geometry": {"type": "Point", "coordinates": [5.4, 43.5]}},
        ],
    )
    def test_rejects_unusable_features(self, feature):
        with pytest.raises(TerritoryUnavailable):
            from_feature(feature)


class TestFetch:
    def test_arrondissement_asks_its_city_name(self):
        with api(LYON_1, {"nom": "Lyon", "code": "69123"}) as urlopen:
            data = territories.fetch("69381")

        assert data.city_name == "Lyon"
        first = urlopen.call_args_list[0].args[0].full_url
        assert first.startswith("https://geo.api.gouv.fr/communes/69381?")
        assert "arrondissement-municipal" in first

    def test_rejects_what_is_not_an_insee_code(self):
        with pytest.raises(TerritoryUnavailable):
            territories.fetch("../etc")

    def test_service_down(self):
        with patch("core.territories.urlopen", side_effect=TimeoutError):
            with pytest.raises(TerritoryUnavailable):
                territories.fetch("13001")


@pytest.mark.django_db
class TestApply:
    def test_saves_and_tells_when_the_outline_changed(self):
        assert territories.apply(from_feature(AIX)) is True
        assert territories.apply(from_feature(AIX)) is False

        territory = Territory.current()
        assert territory.name == "Aix-en-Provence"
        assert territory.postal_code_list == ["13090", "13100"]
        assert territory.boundary == SQUARE

    def test_geocoding_follows(self, territory):
        assert geocoding.city_code() == "13055"

        territories.apply(from_feature(AIX))

        assert geocoding.city_code() == "13001"


@pytest.mark.django_db
class TestCommand:
    def test_from_file_with_overrides(self, tmp_path):
        path = tmp_path / "aix.geojson"
        path.write_text(json.dumps(AIX))

        call_command(
            "configure_territory",
            "--file",
            str(path),
            "--name-in",
            "au pays d'Aix",
            "--postal-codes",
            "13100",
            "--no-tiles",
            stdout=io.StringIO(),
        )

        territory = Territory.current()
        assert territory.name_in == "au pays d'Aix"
        assert territory.postal_codes == "13100"

    def test_from_code_fetches_the_tiles(self):
        with (
            api(AIX),
            patch("publications.map_tiles.queue_refresh") as queue_refresh,
        ):
            call_command("configure_territory", "13001", stdout=io.StringIO())

        assert Territory.current().city_code == "13001"
        queue_refresh.assert_called_once()

    @pytest.mark.parametrize("args", [[], ["13001", "--file", "x.geojson"]])
    def test_code_or_file(self, args):
        with pytest.raises(CommandError):
            call_command("configure_territory", *args)

    def test_service_down(self):
        with patch("core.territories.urlopen", side_effect=TimeoutError):
            with pytest.raises(CommandError):
                call_command("configure_territory", "13001")


@pytest.mark.django_db
class TestBoundaryView:
    def test_not_found_before_the_territory_is_set(self, client):
        assert client.get(reverse("territory_boundary")).status_code == 404

    def test_serves_the_outline_with_a_long_cache(self, client, territory):
        response = client.get(reverse("territory_boundary"))

        assert response.status_code == 200
        assert response.json()["geometry"] == territory.boundary
        assert "max-age=2592000" in response["Cache-Control"]


@pytest.mark.django_db
class TestTexts:
    def test_feed_names_the_area(self, client, territory):
        content = client.get(reverse("publications_rss")).content.decode()

        assert territory.name_in in content

    def test_address_error_names_the_city(self, territory):
        from core.views.auth_mixins import AddressFieldMixin

        form = AddressFieldMixin()
        form.cleaned_data = {"address": "nowhere at all"}
        with patch("core.geocoding.geocode", return_value=None):
            with pytest.raises(Exception, match="à Marseille"):
                form.clean_address()

    def test_projects_map_names_the_area(self, rf, territory):
        from django.template.loader import render_to_string

        html = render_to_string(
            "publications/components/projects_map.html",
            {"projects_map": {"features": []}, "map_config": {}},
            request=rf.get("/"),
        )

        assert territory.name_in in html

    def test_projects_map_without_territory(self, rf, db):
        from django.template.loader import render_to_string

        html = render_to_string(
            "publications/components/projects_map.html",
            {"projects_map": {"features": []}, "map_config": {}},
            request=rf.get("/"),
        )

        assert "Marseille" not in html
