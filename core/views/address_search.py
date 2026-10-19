from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET
from django_ratelimit.decorators import ratelimit

from core.geocoding import GeocodingUnavailable, search_addresses


@require_GET
@ratelimit(key="ip", rate="120/m", block=False)
def address_search(request: HttpRequest) -> JsonResponse:
    """Address suggestions for the autocomplete inputs (public: sign-up uses it)."""
    if getattr(request, "limited", False):
        return JsonResponse({"results": [], "error": "rate_limited"}, status=429)
    try:
        results = search_addresses(request.GET.get("q", ""))
    except GeocodingUnavailable:
        return JsonResponse({"results": [], "error": "unavailable"}, status=503)
    return JsonResponse({"results": [a.as_dict() for a in results]})


def _coordinate(value: str | None, limit: float) -> float | None:
    try:
        number = float(value or "")
    except ValueError:
        return None
    return number if -limit <= number <= limit else None


@require_GET
@ratelimit(key="ip", rate="120/m", block=False)
def nearest_associations(request: HttpRequest) -> JsonResponse:
    """The associations, nearest to a point first, for the association pickers (public)."""
    from core.associations import ranked_associations

    if getattr(request, "limited", False):
        return JsonResponse({"results": [], "error": "rate_limited"}, status=429)
    lon = _coordinate(request.GET.get("lon"), 180)
    lat = _coordinate(request.GET.get("lat"), 90)
    if lon is None or lat is None:
        return JsonResponse({"results": [], "error": "invalid"}, status=400)
    point = {"type": "Point", "coordinates": [lon, lat]}
    return JsonResponse(
        {
            "results": [
                {
                    "id": association.pk,
                    "name": association.name,
                    "distance": round(distance) if distance is not None else None,
                }
                for association, distance in ranked_associations(point)
            ]
        }
    )
