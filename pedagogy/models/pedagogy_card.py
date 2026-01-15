from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import RichTextField
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.search import index


class PedagogyCardPage(Page):
    parent_page_types = ["pedagogy.PedagogyIndexPage"]
    child_page_types = []

    @classmethod
    def get_verbose_name(cls):
        return _("Pedagogy Card")

    body = RichTextField(
        blank=True,
        verbose_name=_("Card body content"),
        help_text=_("The main content of the pedagogy card."),
    )

    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Card image"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Card description"),
        help_text=_("A brief description of the pedagogy card."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("description"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        FieldPanel("hero_image"),
        FieldPanel("body"),
    ]
