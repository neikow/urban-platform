import json
from typing import Any

from django import forms
from django.forms import Script
from django.utils.translation import gettext_lazy as _

from publications.geo import map_config


class GeoJSONMapWidget(forms.Textarea):
    """Draw a project location on a map; the GeoJSON geometry is kept in a hidden textarea.

    The map is a <geojson-map-input> custom element (frontend/src/admin/location-input.ts),
    so it initialises itself whenever Wagtail renders the field.
    """

    template_name = "publications/widgets/geojson_map.html"

    class Media:
        css = {"all": ["dist/map.css", "dist/admin-location.css"]}
        js = [Script("dist/admin-location.js", type="module")]

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context["map_config"] = json.dumps(map_config())
        context["help"] = _(
            "Place a marker for a precise spot, or draw a polygon for an area. "
            "Drawing a new shape replaces the previous one."
        )
        return context

    def format_value(self, value: Any) -> str | None:
        # JSONField hands over a dict, or a JSON string when re-rendering a bound form.
        if value in (None, "", "null"):
            return ""
        return value if isinstance(value, str) else json.dumps(value)
