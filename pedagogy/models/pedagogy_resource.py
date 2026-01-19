from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel
from wagtail.models import Orderable
from django.utils.translation import gettext_lazy as _


class PedagogyResource(Orderable):
    page = ParentalKey(
        "pedagogy.PedagogyCardPage",
        on_delete=models.CASCADE,
        related_name="resources",
    )
    url = models.URLField(blank=True, verbose_name=_("External URL"))
    document = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("File Document"),
    )

    panels = [
        FieldPanel("url"),
        FieldPanel("document"),
    ]

    def clean(self):
        super().clean()
        if self.url and self.document:
            raise ValidationError(
                _("Please provide either a URL or a Document, but not both.")
            )
        if not self.url and not self.document:
            raise ValidationError(_("Please provide either a URL or a Document."))
