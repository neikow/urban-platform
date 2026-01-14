from django.db import models


class CityDistrict(models.Model):
    city = models.ForeignKey("City", on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=100)
    name_short = models.CharField(max_length=50, blank=True)
