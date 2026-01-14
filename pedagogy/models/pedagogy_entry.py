from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from wagtail.search import index


class PedagogyEntry(Page):
    """
    A Page model representing a pedagogy entry.
    """

    body = RichTextField()
    date_published = models.DateField(_("Date Published"))

    search_fields = Page.search_fields + [
        index.SearchField("body"),
        index.FilterField("date_published"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
