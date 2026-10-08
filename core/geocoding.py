"""French address search and geocoding, restricted to Marseille.

Backed by the national address database (Base Adresse Nationale) through the
IGN Géoplateforme geocoding service: free, no key, about 50 requests per
second per IP. Browsers never call it directly: they go through
``core.views.address_search``, so the service only sees the server.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache

logger = logging.getLogger(__name__)

SEARCH_URL = "https://data.geopf.fr/geocodage/search"
# Marseille as a whole: the service expands it to the 16 arrondissements
# (INSEE 13201 to 13216), which are the codes the addresses carry.
CITY_CODE = "13055"
TIMEOUT_SECONDS = 3
CACHE_SECONDS = 60 * 60 * 24
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 200
# Below this score, a free-text address matched something else entirely.
MIN_GEOCODE_SCORE = 0.5


class GeocodingUnavailable(Exception):
    """The geocoding service could not be reached or answered nonsense."""


@dataclass(frozen=True)
class Address:
    label: str
    postcode: str
    lon: float
    lat: float
    score: float

    @property
    def point(self) -> dict[str, Any]:
        """GeoJSON Point geometry (longitude first)."""
        return {"type": "Point", "coordinates": [self.lon, self.lat]}

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fetch(query: str, limit: int, autocomplete: bool) -> list[Address]:
    params = {
        "q": query,
        "index": "address",
        "citycode": CITY_CODE,
        "limit": limit,
        "autocomplete": int(autocomplete),
    }
    cache_key = "geocoding:" + hashlib.sha256(urlencode(params).encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return [Address(**item) for item in cached]

    request = Request(f"{SEARCH_URL}?{urlencode(params)}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310: fixed https URL
            data = json.load(response)
        addresses = [
            Address(
                label=feature["properties"]["label"],
                postcode=feature["properties"].get("postcode", ""),
                lon=feature["geometry"]["coordinates"][0],
                lat=feature["geometry"]["coordinates"][1],
                score=feature["properties"].get("score", 0),
            )
            for feature in data.get("features", [])
        ]
    except (URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as error:
        logger.warning("Geocoding failed for %r: %s", query, error)
        raise GeocodingUnavailable from error

    cache.set(cache_key, [a.as_dict() for a in addresses], CACHE_SECONDS)
    return addresses


def _normalize(query: str) -> str:
    return " ".join(query.split())[:MAX_QUERY_LENGTH]


def search_addresses(query: str, limit: int = 5) -> list[Address]:
    """Suggestions for a partly typed address, best first."""
    query = _normalize(query)
    if len(query) < MIN_QUERY_LENGTH:
        return []
    return _fetch(query, limit, autocomplete=True)


def geocode(address: str) -> Address | None:
    """The Marseille address best matching a full address, or None if there is none.

    Raises GeocodingUnavailable when the service cannot answer.
    """
    query = _normalize(address)
    if len(query) < MIN_QUERY_LENGTH:
        return None
    results = _fetch(query, 1, autocomplete=False)
    if not results or results[0].score < MIN_GEOCODE_SCORE:
        return None
    return results[0]


def locate(address: str, current: dict[str, Any] | None) -> dict[str, Any] | None:
    """GeoJSON Point for an address, keeping ``current`` when the service is down."""
    if not address.strip():
        return None
    try:
        found = geocode(address)
    except GeocodingUnavailable:
        return current
    return found.point if found else None
