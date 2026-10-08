"""Setting the territory (core.models.Territory) from the official French boundaries.

The outline, the postal codes and the names come from geo.api.gouv.fr, for a
commune or a municipal arrondissement (Paris, Lyon, Marseille), given by its
INSEE code. A GeoJSON Feature saved from the same service works offline
(``core/fixtures/marseille-7e.geojson``, for development and tests).
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError

from publications.geo import validate_area

GEO_API_URL = "https://geo.api.gouv.fr/communes/{code}"
TIMEOUT_SECONDS = 10
FIXTURES = Path(__file__).resolve().parent / "fixtures"
MARSEILLE_7E = FIXTURES / "marseille-7e.geojson"

# "Marseille 7e Arrondissement", "Lyon 1er Arrondissement"
ARRONDISSEMENT_NAME = re.compile(r"^(?P<city>.+) (?P<rank>\d+(?:er|e)) Arrondissement$")


class TerritoryUnavailable(Exception):
    """The boundaries could not be fetched, or are not usable."""


@dataclass
class TerritoryData:
    name: str
    name_in: str
    city_name: str
    city_code: str
    postal_codes: list[str] = field(default_factory=list)
    boundary: dict[str, Any] | None = None

    def fields(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "name_in": self.name_in,
            "city_name": self.city_name,
            "city_code": self.city_code,
            "postal_codes": ", ".join(self.postal_codes),
            "boundary": self.boundary,
        }


def _get(code: str, **params: str) -> dict[str, Any]:
    query = urlencode({"type": "commune-actuelle,arrondissement-municipal", **params})
    request = Request(
        f"{GEO_API_URL.format(code=code)}?{query}", headers={"Accept": "application/json"}
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310: fixed https URL
            return dict(json.load(response))
    except (URLError, TimeoutError, ValueError) as error:
        raise TerritoryUnavailable(f"geo.api.gouv.fr did not answer for {code}: {error}") from error


def from_feature(feature: dict[str, Any], city_name: str | None = None) -> TerritoryData:
    """Territory data from a geo.api.gouv.fr commune Feature (properties nom, code…).

    ``city_name`` names the city of an arrondissement; it is read from its name otherwise.
    """
    try:
        properties = feature["properties"]
        name, code, geometry = properties["nom"], properties["code"], feature["geometry"]
    except (KeyError, TypeError) as error:
        raise TerritoryUnavailable("Not a commune Feature from geo.api.gouv.fr.") from error
    try:
        validate_area(geometry)
    except ValidationError as error:
        raise TerritoryUnavailable("The outline is not a polygon.") from error

    postal_codes = sorted(properties.get("codesPostaux") or [])
    if parent := properties.get("codeParent"):
        match = ARRONDISSEMENT_NAME.match(name)
        city = city_name or (match["city"] if match else name)
        label = f"{match['rank']} arrondissement de {city}" if match else name
        return TerritoryData(
            name=label,
            name_in=f"dans le {label}" if match else f"à {name}",
            city_name=city,
            city_code=parent,
            postal_codes=postal_codes,
            boundary=geometry,
        )
    return TerritoryData(
        name=name,
        name_in=f"à {name}",
        city_name=name,
        city_code=code,
        postal_codes=postal_codes,
        boundary=geometry,
    )


def fetch(code: str) -> TerritoryData:
    """Territory data of a commune or an arrondissement, by INSEE code (e.g. 13207)."""
    if not re.fullmatch(r"\d[\dAB]\d{3}", code):
        raise TerritoryUnavailable(f"{code!r} is not an INSEE code.")
    feature = _get(
        code,
        fields="nom,code,codesPostaux,codeParent,contour",
        format="geojson",
        geometry="contour",
    )
    city_name = None
    if parent := feature.get("properties", {}).get("codeParent"):
        city_name = _get(parent, fields="nom").get("nom")
    return from_feature(feature, city_name)


def from_file(path: Path) -> TerritoryData:
    try:
        feature = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise TerritoryUnavailable(f"Could not read {path}: {error}") from error
    return from_feature(feature)


def apply(data: TerritoryData) -> bool:
    """Save the territory. Returns whether the outline changed (the tiles must follow)."""
    from core.cache import clear_content_cache
    from core.models import Territory

    territory = Territory.current()
    changed = territory.boundary != data.boundary
    for name, value in data.fields().items():
        setattr(territory, name, value)
    territory.full_clean()
    territory.save()
    # Cached page fragments embed the map settings and the area's name.
    clear_content_cache()
    return changed
