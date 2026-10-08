import json
import re

import pytest
from django.core.exceptions import ValidationError

from publications.geo import (
    LOCAL_AREA_CENTER,
    area_contains,
    map_config,
    validate_area,
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
    def test_points_to_the_self_hosted_tiles(self):
        config = map_config()

        assert config["tilesUrl"].endswith(".pmtiles")
        assert config["tilesUrl"].startswith("/static/")

    def test_max_bounds_contain_the_initial_view(self):
        (south, west), (north, east) = map_config()["maxBounds"]
        lat, lon = LOCAL_AREA_CENTER

        assert south < lat < north
        assert west < lon < east
