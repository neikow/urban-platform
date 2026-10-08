from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from publications.geo import validate_area

from .user import UserRole


class NeighborhoodAssociation(models.Model):
    name = models.CharField(_("Name"), max_length=150)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    # Filled from the address when saving (core.geocoding), for the maps.
    address_location = models.JSONField(
        _("Address location"), null=True, blank=True, editable=False
    )
    area = models.JSONField(
        _("Area"),
        null=True,
        blank=True,
        validators=[validate_area],
        help_text=_("Residents whose address lies in this area are attached to the association."),
    )
    responsible = models.ForeignKey(
        "User",
        verbose_name=_("Responsible"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_for_associations",
        limit_choices_to={"role__in": [UserRole.ASSOCIATION_MEMBER, UserRole.ADMIN]},
    )
    contact_email = models.EmailField(_("Contact Email"), blank=True)
    contact_phone = models.CharField(_("Phone Number"), max_length=20, blank=True)
    website = models.URLField(_("Website"), blank=True)

    class Meta:
        verbose_name = _("Neighborhood Association")
        verbose_name_plural = _("Neighborhood Associations")
        ordering = ["name"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # The area as loaded, to tell whether saving changed it (core.associations).
        self.loaded_area = self.area

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        from core.geocoding import locate

        super().clean()
        self.address_location = locate(self.address, self.address_location)

    def area_feature(self) -> dict[str, Any]:
        """GeoJSON Feature of the area, for the maps."""
        return {
            "type": "Feature",
            "geometry": self.area,
            "properties": {"id": self.pk, "name": self.name},
        }
