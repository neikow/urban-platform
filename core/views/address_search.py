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
