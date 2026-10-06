import json
import re

import pytest
from django.core.exceptions import ValidationError

from publications.geo import validate_geometry
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


class TestWidget:
    def test_renders_custom_element_with_geometry(self):
        html = GeoJSONMapWidget().render("location", POINT)

        assert "<geojson-map-input" in html
        assert json.dumps(POINT).replace('"', "&quot;") in html
        assert "boundaryUrl" in html.replace("&quot;", '"')

    def test_renders_empty_value(self):
        html = GeoJSONMapWidget().render("location", None)

        assert re.search(r"<textarea[^>]*></textarea>", html)

    def test_media_loads_the_module_bundle(self):
        media = str(GeoJSONMapWidget().media)

        assert 'type="module"' in media
        assert "dist/admin-location.js" in media
