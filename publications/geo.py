"""Project locations stored as GeoJSON geometries (no PostGIS needed).

A location is either a Point (a precise spot) or a Polygon (an area, e.g. a
street or a park), in WGS84 longitude/latitude as GeoJSON mandates.
"""

import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from publications.models import ProjectPage

ALLOWED_GEOMETRY_TYPES = ("Point", "Polygon")

# The local area (its outline, its name) is the Territory setting (core.models).
# Before it is set, the maps show metropolitan France.
DEFAULT_CENTER = (46.6, 2.4)  # lat, lon
DEFAULT_ZOOM = 5
DEFAULT_TILES_BOUNDS = (-5.5, 41.2, 9.8, 51.2)  # west, south, east, north
# Used before the outline has loaded and as the admin widget's default view.
LOCAL_AREA_ZOOM = 14

# Self-hosted basemap: a PMTiles extract fetched by the `refresh_map_tiles` task
# (publications.map_tiles). It covers the outline's bounding box widened on each
# side by four times its span, so the maps open on the outline and zoom out a few
# levels further. The margin is capped, or the extract of a large commune would
# weigh hundreds of MB. The maps cannot be panned outside it: there are no tiles there.
LOCAL_AREA_TILES_PATH = "publications/geo/local-area.pmtiles"
LOCAL_AREA_TILES_MAX_ZOOM = 15  # vector tiles stay sharp when zoomed past it
TILES_MARGIN_SPANS = 4
TILES_MARGIN_MIN = 0.05  # degrees
TILES_MARGIN_MAX = 0.3


def _is_position(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) in (2, 3)
        and all(isinstance(c, int | float) and not isinstance(c, bool) for c in value)
        and -180 <= value[0] <= 180
        and -90 <= value[1] <= 90
    )


def _is_linear_ring(ring: Any) -> bool:
    return (
        isinstance(ring, list)
        and len(ring) >= 4
        and all(_is_position(p) for p in ring)
        and ring[0][:2] == ring[-1][:2]
    )


def validate_geometry(value: Any) -> None:
    """Accept a GeoJSON Point or Polygon geometry, reject anything else."""
    if value in (None, ""):
        return
    if not isinstance(value, dict) or value.get("type") not in ALLOWED_GEOMETRY_TYPES:
        raise ValidationError(_("The location must be a point or a polygon."))

    coordinates = value.get("coordinates")
    if value["type"] == "Point":
        valid = _is_position(coordinates)
    else:
        valid = _is_polygon(coordinates)
    if not valid:
        raise ValidationError(_("The location coordinates are invalid."))


def _is_polygon(coordinates: Any) -> bool:
    return (
        isinstance(coordinates, list)
        and len(coordinates) >= 1
        and all(_is_linear_ring(ring) for ring in coordinates)
    )


def validate_area(value: Any) -> None:
    """Accept a GeoJSON Polygon or MultiPolygon geometry, reject anything else."""
    if value in (None, ""):
        return
    if not isinstance(value, dict) or value.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValidationError(_("The area must be a polygon."))
    coordinates = value.get("coordinates")
    if value["type"] == "Polygon":
        valid = _is_polygon(coordinates)
    else:
        valid = isinstance(coordinates, list) and all(_is_polygon(p) for p in coordinates)
    if not valid or not coordinates:
        raise ValidationError(_("The area coordinates are invalid."))


def _ring_contains(ring: list[list[float]], x: float, y: float) -> bool:
    """Ray casting: count the ring edges a ray going east from (x, y) crosses."""
    inside = False
    for (x1, y1, *_rest), (x2, y2, *_rest2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def area_contains(area: dict[str, Any] | None, point: dict[str, Any] | None) -> bool:
    """Whether a GeoJSON Point lies in a Polygon or MultiPolygon (holes excluded).

    Planar test on longitude/latitude: exact enough at the scale of a city.
    """
    if not area or not point or point.get("type") != "Point":
        return False
    x, y = point["coordinates"][:2]
    polygons = [area["coordinates"]] if area["type"] == "Polygon" else area["coordinates"]
    return any(
        _ring_contains(outer, x, y) and not any(_ring_contains(hole, x, y) for hole in holes)
        for outer, *holes in polygons
    )


def project_feature(project: "ProjectPage") -> dict[str, Any]:
    """GeoJSON Feature describing a project for the public maps."""
    return {
        "type": "Feature",
        "geometry": project.location,
        "properties": {
            "title": project.title,
            "url": project.url,
            "category": project.get_category_display(),
            "description": project.description[:200],
            "participation": project.participation_mode,
            "isOpen": project.is_voting_open or project.is_ideas_open,
        },
    }


def feature_collection(projects: Iterable["ProjectPage"]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [project_feature(p) for p in projects if p.location],
    }


def _polygons(area: dict[str, Any]) -> list[Any]:
    return [area["coordinates"]] if area["type"] == "Polygon" else area["coordinates"]


def bounds(area: dict[str, Any]) -> tuple[float, float, float, float]:
    """Bounding box of a Polygon or MultiPolygon: west, south, east, north."""
    positions = [p for polygon in _polygons(area) for ring in polygon for p in ring]
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    return min(xs), min(ys), max(xs), max(ys)


def _ring_area(ring: list[list[float]]) -> float:
    """Planar area (shoelace formula), enough to compare the polygons of one city."""
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1, *_a), (x2, y2, *_b) in zip(ring, ring[1:]))) / 2


def area_center(area: dict[str, Any]) -> tuple[float, float]:
    """Centre (lat, lon) of the largest polygon: an arrondissement may include islands."""
    largest = max(_polygons(area), key=lambda polygon: _ring_area(polygon[0]))
    west, south, east, north = bounds({"type": "Polygon", "coordinates": largest})
    return round((south + north) / 2, 5), round((west + east) / 2, 5)


def tiles_bounds(area: dict[str, Any] | None) -> tuple[float, float, float, float]:
    """Extent of the basemap extract around an outline (see TILES_MARGIN_SPANS)."""
    if not area:
        return DEFAULT_TILES_BOUNDS
    west, south, east, north = bounds(area)

    def margin(span: float) -> float:
        return min(max(span * TILES_MARGIN_SPANS, TILES_MARGIN_MIN), TILES_MARGIN_MAX)

    def down(value: float) -> float:
        # Rounded first: 42.92 * 100 is 4291.999…
        return math.floor(round(value * 100, 6)) / 100

    def up(value: float) -> float:
        return math.ceil(round(value * 100, 6)) / 100

    dx, dy = margin(east - west), margin(north - south)
    # Rounded outwards: the extract and its file name stay the same for the same outline.
    return down(west - dx), down(south - dy), up(east + dx), up(north + dy)


def map_config() -> dict[str, Any]:
    """Settings shared by the public maps and the admin widget."""
    from core.models import Territory
    from publications.map_tiles import tiles_url

    territory = Territory.current()
    area = territory.boundary
    west, south, east, north = tiles_bounds(area)
    boundary_url = ""
    if area:
        boundary_url = f"{reverse('territory_boundary')}?v={territory.boundary_version}"
    return {
        "boundaryUrl": boundary_url,
        "center": area_center(area) if area else DEFAULT_CENTER,
        "zoom": LOCAL_AREA_ZOOM if area else DEFAULT_ZOOM,
        "tilesUrl": tiles_url(),
        "tilesMaxZoom": LOCAL_AREA_TILES_MAX_ZOOM,
        "maxBounds": [[south, west], [north, east]],
    }
