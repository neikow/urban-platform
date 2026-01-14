from django.db import models
from django.utils.translation import gettext_lazy as _


class NeighborhoodAssociation(models.Model):
    neighborhood = models.ForeignKey(
        "CityNeighborhood", on_delete=models.CASCADE, related_name="associations"
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return f"{_('Neighborhood Association')} ({self.neighborhood.full_name})"
