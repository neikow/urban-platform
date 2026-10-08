from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from core.models import Territory


@require_GET
# The maps ask for it with the outline's version (publications.geo.map_config):
# a new outline means a new URL, so browsers may keep this one.
@cache_control(public=True, max_age=60 * 60 * 24 * 30)
def territory_boundary(request: HttpRequest) -> JsonResponse:
    """The territory outline as a GeoJSON Feature, drawn on the maps."""
    feature = Territory.current(request).boundary_feature()
    if feature is None:
        raise Http404
    return JsonResponse(feature)
