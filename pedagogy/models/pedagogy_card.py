from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel
from typing import override

from wagtail.admin.panels import InlinePanel
from wagtail.models import Page
from wagtail.fields import StreamField
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.search import index

from core.blocks import BlockTypes
from core.toc import TableOfContentsItem, generate_header_ids, get_table_of_contents


class PedagogyCardPage(Page):
    parent_page_types: list[str] = ["pedagogy.PedagogyIndexPage"]
    child_page_types: list[str] = []

    resources: models.Manager  # related manager

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Pedagogy Card")

    content = StreamField(
        BlockTypes,
        blank=True,
        verbose_name=_("Card body content"),
        help_text=_("The main content of the pedagogy card."),
    )

    hero_image: models.ForeignKey = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Card image"),
    )

    description: models.TextField = models.TextField(
        blank=True,
        verbose_name=_("Card description"),
        help_text=_("A brief description of the pedagogy card."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("description"),
        index.SearchField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        FieldPanel("hero_image"),
        InlinePanel("resources", label=_("Resource"), max_num=1),
        FieldPanel("content"),
    ]

    def has_resource(self) -> bool:
        return self.resources.exists()

    @override
    def clean(self) -> None:
        super().clean()

        for block in self.content:
            if block.block_type == "text":
                generate_header_ids(block)

    @property
    def table_of_contents(self) -> list[TableOfContentsItem]:
        return get_table_of_contents(self.content)
