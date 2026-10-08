import json
import re

import pytest
from django.core.exceptions import ValidationError

from publications.geo import (
    DEFAULT_TILES_BOUNDS,
    area_center,
    area_contains,
    bounds,
    map_config,
    validate_area,
    tiles_bounds,
    validate_geometry,
)
from publications.widgets import GeoJSONMapWidget

POINT = {"type": "Point", "coordinates": [5.3601, 43.2841]}
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[5.35, 43.28], [5.36, 43.28], [5.36, 43.29], [5.35, 43.28]]],
}


class TestValidateGeometry:
    @pytest.mark.parametrize(
        "value", [None, "", POINT, POLYGON, {**POINT, "coordinates": [5, 43, 12]}]
    )
    def test_accepts(self, value):
        validate_geometry(value)

    @pytest.mark.parametrize(
        "value",
        [
            {"type": "LineString", "coordinates": [[5, 43], [5.1, 43.1]]},
            {"type": "Point", "coordinates": [500, 43]},
            {"type": "Point", "coordinates": ["5", "43"]},
            {"type": "Point", "coordinates": [True, 43]},
            {"type": "Polygon", "coordinates": [[[5, 43], [5.1, 43], [5, 43.1]]]},  # too short
            {
                "type": "Polygon",
                "coordinates": [[[5, 43], [5.1, 43], [5.1, 43.1], [5, 43.2]]],
            },  # open
            {"type": "Polygon", "coordinates": []},
            [5, 43],
            "POINT(5 43)",
        ],
    )
    def test_rejects(self, value):
        with pytest.raises(ValidationError):
            validate_geometry(value)


SQUARE = [[5.0, 43.0], [5.1, 43.0], [5.1, 43.1], [5.0, 43.1], [5.0, 43.0]]
HOLE = [[5.04, 43.04], [5.06, 43.04], [5.06, 43.06], [5.04, 43.06], [5.04, 43.04]]
DONUT = {"type": "Polygon", "coordinates": [SQUARE, HOLE]}
ISLANDS = {
    "type": "MultiPolygon",
    "coordinates": [[SQUARE], [[[5.2, 43.0], [5.3, 43.0], [5.3, 43.1], [5.2, 43.0]]]],
}


def point(lon, lat):
    return {"type": "Point", "coordinates": [lon, lat]}


class TestValidateArea:
    @pytest.mark.parametrize("value", [None, "", POLYGON, DONUT, ISLANDS])
    def test_accepts(self, value):
        validate_area(value)

    @pytest.mark.parametrize(
        "value",
        [
            POINT,
            {"type": "Polygon", "coordinates": []},
            {"type": "MultiPolygon", "coordinates": []},
            {"type": "Polygon", "coordinates": [[[5, 43], [5.1, 43], [5.2, 43.1]]]},
        ],
    )
    def test_rejects(self, value):
        with pytest.raises(ValidationError):
            validate_area(value)


class TestAreaContains:
    def test_polygon_with_hole(self):
        assert area_contains(DONUT, point(5.02, 43.02))
        assert not area_contains(DONUT, point(5.05, 43.05))
        assert not area_contains(DONUT, point(5.2, 43.05))

    def test_multipolygon(self):
        assert area_contains(ISLANDS, point(5.05, 43.05))
        assert area_contains(ISLANDS, point(5.28, 43.02))
        assert not area_contains(ISLANDS, point(5.15, 43.05))

    def test_nothing_to_compare(self):
        assert not area_contains(None, point(5.05, 43.05))
        assert not area_contains(DONUT, None)


@pytest.mark.django_db
class TestWidget:
    def test_renders_custom_element_with_geometry(self):
        html = GeoJSONMapWidget().render("location", POINT)

        assert "<geojson-map-input" in html
        assert json.dumps(POINT).replace('"', "&quot;") in html
        assert "boundaryUrl" in html.replace("&quot;", '"')

    def test_renders_empty_value(self):
        html = GeoJSONMapWidget().render("location", None)

        assert re.search(r"<textarea[^>]*></textarea>", html)

    def test_area_only_widget_with_reference_shapes(self):
        reference = {"type": "FeatureCollection", "features": []}
        html = GeoJSONMapWidget(markers=False, reference=lambda: reference).render("area", None)
        config = re.search(r'data-config="([^"]*)"', html)

        assert config and json.loads(config.group(1).replace("&quot;", '"'))["markers"] is False
        assert "data-reference=" in html
        assert "data-search" in html

    def test_media_loads_the_module_bundle(self):
        media = str(GeoJSONMapWidget().media)

        assert 'type="module"' in media
        assert "dist/admin-location.js" in media


@pytest.mark.django_db
class TestMapConfig:
    def test_shows_france_before_the_territory_is_set(self):
        config = map_config()

        assert config["boundaryUrl"] == ""
        (south, west), (north, east) = config["maxBounds"]
        assert (west, south, east, north) == DEFAULT_TILES_BOUNDS

    def test_opens_on_the_territory(self, territory):
        config = map_config()
        (south, west), (north, east) = config["maxBounds"]
        lat, lon = config["center"]

        assert config["boundaryUrl"].endswith(f"?v={territory.boundary_version}")
        assert south < lat < north
        assert west < lon < east

    def test_new_outline_new_url(self, territory):
        before = map_config()["boundaryUrl"]
        territory.boundary = SQUARE_AREA
        territory.save()

        assert map_config()["boundaryUrl"] != before


SQUARE_AREA = {"type": "Polygon", "coordinates": [SQUARE]}
ISLAND = [[[5.5, 43.5], [5.51, 43.5], [5.51, 43.51], [5.5, 43.5]]]


class TestExtent:
    def test_bounds(self):
        assert bounds(SQUARE_AREA) == (5.0, 43.0, 5.1, 43.1)

    def test_center_ignores_small_islands(self):
        area = {"type": "MultiPolygon", "coordinates": [ISLAND, [SQUARE]]}

        assert area_center(area) == (43.05, 5.05)

    def test_tiles_cover_the_surroundings(self):
        small = {
            "type": "Polygon",
            "coordinates": [[[5.0, 43.0], [5.05, 43.0], [5.05, 43.02], [5.0, 43.0]]],
        }

        # Four times the span on each side (at least 0.05°), rounded outwards.
        assert tiles_bounds(small) == (4.8, 42.92, 5.25, 43.1)

    def test_tiles_margin_is_capped(self):
        large = {
            "type": "Polygon",
            "coordinates": [[[4.0, 43.0], [5.0, 43.0], [5.0, 44.0], [4.0, 43.0]]],
        }

        assert tiles_bounds(large) == (3.7, 42.7, 5.3, 44.3)

    def test_without_outline(self):
        assert tiles_bounds(None) == DEFAULT_TILES_BOUNDS
