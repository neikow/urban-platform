from django.db import models


class CityNeighborhood(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(
        "CityDistrict", on_delete=models.CASCADE, related_name="neighborhoods"
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    @property
    def full_name(self):
        return f"{self.name}, {self.district.name}"
