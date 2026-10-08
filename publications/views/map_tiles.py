from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core import task_monitor


@require_POST
def refresh_map_tiles(request: HttpRequest) -> HttpResponseRedirect:
    """Fetch the latest map tiles now, in the background (Settings › Map)."""
    if not request.user.has_perm("publications.change_mapsettings"):
        raise PermissionDenied
    trigger = task_monitor.get_trigger("map_tiles")
    if trigger is not None and task_monitor.launch(trigger, request.user):
        messages.success(
            request,
            _("The map update has started. It takes a few minutes: reload this page to see it."),
        )
    else:
        messages.warning(request, _("A map update is already in progress."))
    return HttpResponseRedirect(
        reverse("wagtailsettings:edit", args=["publications", "mapsettings"])
    )
