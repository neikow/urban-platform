from dataclasses import dataclass
from typing import override

from slugify import slugify
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.blocks import StreamValue
from wagtail.models import Page
from wagtail.fields import StreamField
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.search import index

from core.blocks import BlockTypes


@dataclass
class TableOfContentsItem:
    title: str
    id: str
    level: int


def _generate_paragraph_header_ids(block: StreamValue.StreamChild) -> None:
    html = block.value.source
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for header in soup.find_all(["h2", "h3", "h4"]):
        header_id = slugify(header.get_text())
        header["id"] = header_id
    block.value.source = str(soup)


class PedagogyCardPage(Page):
    parent_page_types = ["pedagogy.PedagogyIndexPage"]
    child_page_types = []

    resources: models.Manager  # related manager

    @classmethod
    def get_verbose_name(cls):
        return _("Pedagogy Card")

    content = StreamField(
        BlockTypes,
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
                _generate_paragraph_header_ids(block)

    @property
    def table_of_contents(self) -> list[TableOfContentsItem]:
        toc: list[TableOfContentsItem] = []

        for block in self.content:
            if block.block_type == "text":
                html = block.value.source
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")
                for header in soup.find_all(["h2", "h3", "h4"]):
                    level = int(header.name[1])
                    title = header.get_text()
                    id_attr = header.get("id", "")

                    if not id_attr:
                        continue

                    toc.append(
                        TableOfContentsItem(title=title, id=id_attr, level=level)
                    )

        return toc
