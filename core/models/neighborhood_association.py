from django.db import models
from django.utils.translation import gettext_lazy as _


class NeighborhoodAssociation(models.Model):
    neighborhood = models.ForeignKey(
        "CityNeighborhood",
        verbose_name=_("City Neighborhood"),
        on_delete=models.CASCADE,
        related_name="associations",
    )
    contact_email = models.EmailField(_("Contact Email"), blank=True)
    contact_phone = models.CharField(_("Contact Phone"), max_length=20, blank=True)
    website = models.URLField(_("Website"), blank=True)

    class Meta:
        verbose_name = _("Neighborhood Association")
        verbose_name_plural = _("Neighborhood Associations")
        ordering = [
            "neighborhood__district__city__name",
            "neighborhood__district__name",
            "neighborhood__name",
        ]

    def __str__(self):
        return f"{_('Neighborhood Association')} ({self.neighborhood.full_name})"
