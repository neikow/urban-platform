from django.db import models
from django.utils.translation import gettext_lazy as _


class RubricCode(models.TextChoices):
    """The fixed set of rubrics a project can belong to (one or more)."""

    HOUSING = "HOUSING", _("Housing")
    PARKS_GARDENS = "PARKS_GARDENS", _("Parks & Gardens")
    PUBLIC_SPACE = "PUBLIC_SPACE", _("Public space")
    HERITAGE = "HERITAGE", _("Heritage")


# Display order, which is also the order of the filter chips.
RUBRIC_ORDER = list(RubricCode.values)


class Rubric(models.Model):
    """One row per :class:`RubricCode`, created by a migration.

    A table (rather than a list of codes on the page) so projects can be
    filtered by rubric in SQL and revisions keep the selection like any other
    many-to-many field. The label comes from the code, so it is translated.
    """

    code: models.CharField[str, str] = models.CharField(
        _("Code"), max_length=30, choices=RubricCode.choices, unique=True
    )
    sort_order: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField(
        default=0
    )

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Rubric")
        verbose_name_plural = _("Rubrics")

    def __str__(self) -> str:
        return str(self.get_code_display())
