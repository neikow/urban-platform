from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, Panel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


class MapTilesStatusPanel(Panel):
    """What the refresh task last did, read-only (empty values shown as a dash)."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "publications/admin/map_tiles_status.html"

        def get_context_data(self, parent_context: Any = None) -> dict[str, Any]:
            from publications.map_tiles import is_refreshing

            context = super().get_context_data(parent_context)
            context["refreshing"] = is_refreshing()
            context["refresh_url"] = reverse("map_tiles_refresh")
            return context


@register_setting(icon="site")
class MapSettings(BaseGenericSetting):
    """How often the basemap is refreshed from OpenStreetMap (publications.map_tiles)."""

    tiles_auto_update = models.BooleanField(
        _("Update the map automatically"),
        default=True,
        help_text=_("Download the latest OpenStreetMap data for the maps at the interval below."),
    )
    tiles_update_interval_days = models.PositiveSmallIntegerField(
        _("Update interval (days)"),
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text=_(
            "Streets and places change slowly: once a month is enough. "
            "Each update downloads 35 to 60 MB, depending on the territory."
        ),
    )

    # Written by the refresh task, shown read-only.
    tiles_build = models.CharField(_("Map data version"), max_length=50, blank=True, editable=False)
    tiles_file = models.CharField(max_length=255, blank=True, editable=False)
    tiles_updated_at = models.DateTimeField(_("Last update"), null=True, blank=True, editable=False)
    tiles_checked_at = models.DateTimeField(_("Last check"), null=True, blank=True, editable=False)
    tiles_error = models.TextField(_("Last error"), blank=True, editable=False)

    panels = [
        FieldPanel("tiles_auto_update"),
        FieldPanel("tiles_update_interval_days"),
        MapTilesStatusPanel(heading=_("Status")),
    ]

    class Meta:
        verbose_name = _("Map")
