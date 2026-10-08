import hashlib
import json
from typing import Any

from django.db import models
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, HelpPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting

from publications.geo import validate_area


@register_setting(icon="globe")
class Territory(BaseGenericSetting):
    """The area the website covers: its outline, how to name it, where addresses are searched.

    Set when the website is installed (``manage.py configure_territory``), from
    the official boundaries of a commune or an arrondissement. The maps open on
    the outline and their tiles cover its surroundings (publications.geo).
    """

    name = models.CharField(
        _("Name"),
        max_length=150,
        blank=True,
        help_text=_('Shown alone, e.g. "7e arrondissement de Marseille".'),
    )
    name_in = models.CharField(
        _("Name in a sentence"),
        max_length=160,
        blank=True,
        help_text=_(
            'Completes "Projects located…", e.g. "dans le 7e arrondissement de Marseille".'
        ),
    )
    city_name = models.CharField(
        _("City"),
        max_length=100,
        blank=True,
        help_text=_("Addresses are searched in this city, e.g. Marseille."),
    )
    city_code = models.CharField(
        _("City INSEE code"),
        max_length=5,
        blank=True,
        help_text=_(
            "Official code of the commune (not the postal code), e.g. 13055 for Marseille. "
            "Empty: addresses are searched in the whole of France."
        ),
    )
    postal_codes = models.CharField(
        _("Local postal codes"),
        max_length=200,
        blank=True,
        help_text=_(
            "Separated by commas. The participation statistics count residents with "
            "these postal codes by default. Empty: everyone is counted."
        ),
    )
    # Polygon or MultiPolygon, from geo.api.gouv.fr. Not edited in the admin.
    boundary = models.JSONField(_("Boundary"), null=True, blank=True, validators=[validate_area])

    panels = [
        HelpPanel(
            content=_(
                "The outline of the area is set when the website is installed. "
                "Contact the support to change it."
            )
        ),
        FieldPanel("name"),
        FieldPanel("name_in"),
        FieldPanel("city_name"),
        FieldPanel("city_code"),
        FieldPanel("postal_codes"),
    ]

    class Meta:
        verbose_name = _("Territory")

    @classmethod
    def current(cls, request: HttpRequest | None = None) -> "Territory":
        return cls.load(request_or_site=request)

    @property
    def postal_code_list(self) -> list[str]:
        return [code.strip() for code in self.postal_codes.split(",") if code.strip()]

    @property
    def boundary_version(self) -> str:
        """Changes with the outline: appended to its URL so caches never serve an old one."""
        if not self.boundary:
            return ""
        encoded = json.dumps(self.boundary, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()[:12]

    def boundary_feature(self) -> dict[str, Any] | None:
        if not self.boundary:
            return None
        return {"type": "Feature", "properties": {"name": self.name}, "geometry": self.boundary}
