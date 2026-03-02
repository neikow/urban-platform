from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel
from wagtail.models import Orderable
from django.utils.translation import gettext_lazy as _


class ProjectExternalLink(Orderable):
    """
    External link for a project page.
    Allows projects to link to external resources as CTA buttons.
    """

    page = ParentalKey(
        "publications.ProjectPage",
        on_delete=models.CASCADE,
        related_name="external_links",
    )
    title: models.CharField = models.CharField(
        _("Button Text"),
        max_length=255,
        help_text=_("Text displayed on the button"),
    )
    url: models.URLField = models.URLField(
        _("URL"),
        help_text=_("External URL for this link"),
    )
    tooltip: models.CharField = models.CharField(
        _("Tooltip"),
        max_length=255,
        blank=True,
        help_text=_("Text shown on hover (optional)"),
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("url"),
        FieldPanel("tooltip"),
    ]

    def __str__(self) -> str:
        return str(self.title)

    def clean(self) -> None:
        super().clean()
        if not self.url:
            raise ValidationError(_("URL is required for external links."))

    class Meta:
        verbose_name = _("External Link")
        verbose_name_plural = _("External Links")
        ordering = ["sort_order"]
