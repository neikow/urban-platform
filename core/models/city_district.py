from django.db import models
from django.utils.translation import gettext_lazy as _


class CityDistrict(models.Model):
    city = models.ForeignKey("City", on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=100)
    name_short = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = _("City District")
        verbose_name_plural = _("City Districts")
        ordering = ["city__name", "name"]
