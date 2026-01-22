from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectImage(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Project"),
    )

    image = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("Image"),
    )

    caption = models.CharField(
        _("Caption"),
        max_length=255,
        blank=True,
    )

    order = models.PositiveIntegerField(
        _("Order"),
        default=0,
    )

    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Project Image")
        verbose_name_plural = _("Project Images")
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.project.title} - Image {self.order}"
