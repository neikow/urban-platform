from django.db import models
from django.utils.translation import gettext_lazy as _


class CityNeighborhood(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(
        "CityDistrict", on_delete=models.CASCADE, related_name="neighborhoods"
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = _("City Neighborhood")
        verbose_name_plural = _("City Neighborhoods")
        ordering = ["district__city__name", "district__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.district.name})"

    @property
    def full_name(self):
        return f"{self.name}, {self.district.name}"
