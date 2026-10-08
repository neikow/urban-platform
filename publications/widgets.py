import json
from collections.abc import Callable
from typing import Any

from django import forms
from django.forms import Script
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise

from publications.geo import map_config


class GeoJSONMapWidget(forms.Textarea):
    """Draw a location on a map; the GeoJSON geometry is kept in a hidden textarea.

    The map is a <geojson-map-input> custom element (frontend/src/admin/location-input.ts),
    so it initialises itself whenever Wagtail renders the field. An address search
    above the map moves it there, and places the marker when markers are allowed.

    ``reference`` returns a FeatureCollection drawn underneath, read-only but
    snappable (e.g. the other associations' areas), with a ``name`` property.
    """

    template_name = "publications/widgets/geojson_map.html"

    class Media:
        css = {"all": ["dist/map.css", "dist/admin-location.css", "dist/address-autocomplete.css"]}
        js = [Script("dist/admin-location.js", type="module")]

    def __init__(
        self,
        attrs: dict[str, Any] | None = None,
        *,
        markers: bool = True,
        help_text: StrOrPromise | None = None,
        reference: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(attrs)
        self.markers = markers
        self.help_text = help_text
        self.reference = reference

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        config = map_config()
        config["markers"] = self.markers
        config["searchUrl"] = reverse("address_search")
        context["map_config"] = json.dumps(config)
        context["reference"] = json.dumps(self.reference()) if self.reference else ""
        context["help"] = self.help_text or _(
            "Place a marker for a precise spot, or draw a polygon for an area. "
            "Drawing a new shape replaces the previous one."
        )
        return context

    def format_value(self, value: Any) -> str | None:
        # JSONField hands over a dict, or a JSON string when re-rendering a bound form.
        if value in (None, "", "null"):
            return ""
        return value if isinstance(value, str) else json.dumps(value)
