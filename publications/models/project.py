from dataclasses import dataclass

from bs4 import BeautifulSoup
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from slugify import slugify
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import StreamValue
from wagtail.search import index

from publications.models.publication import PublicationPage


@dataclass
class TableOfContentsItem:
    title: str
    id: str
    level: int


def _generate_paragraph_header_ids(block: StreamValue.StreamChild) -> None:
    html = block.value.source

    soup = BeautifulSoup(html, "html.parser")
    for header in soup.find_all(["h2", "h3", "h4"]):
        header_id = slugify(header.get_text())
        header["id"] = header_id
    block.value.source = str(soup)


class ProjectCategory(models.TextChoices):
    URBAN_PLANNING = "URBAN_PLANNING", _("Urban Planning")
    ENVIRONMENT = "ENVIRONMENT", _("Environment")
    MOBILITY = "MOBILITY", _("Mobility")
    HOUSING = "HOUSING", _("Housing")
    CULTURE = "CULTURE", _("Culture")
    SPORT = "SPORT", _("Sport")
    EDUCATION = "EDUCATION", _("Education")
    HEALTH = "HEALTH", _("Health")
    SOCIAL = "SOCIAL", _("Social")
    ECONOMY = "ECONOMY", _("Economy")
    OTHER = "OTHER", _("Other")


class ProjectPage(PublicationPage):
    parent_page_types: list[str] = ["publications.PublicationIndexPage"]
    child_page_types: list[str] = []

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Project")

    category: models.CharField[str, str] = models.CharField(
        _("Category"),
        max_length=30,
        choices=ProjectCategory.choices,
        default=ProjectCategory.OTHER,
    )

    search_fields = PublicationPage.search_fields + [
        index.SearchField("category"),
    ]

    content_panels = PublicationPage.content_panels + [
        FieldPanel("category"),
    ]

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

                soup = BeautifulSoup(html, "html.parser")
                for header in soup.find_all(["h2", "h3", "h4"]):
                    level = int(header.name[1])
                    title = header.get_text()
                    id_attr = header.get("id", "")
                    if not id_attr:
                        id_attr = slugify(title)

                    if not id_attr or not isinstance(id_attr, str):
                        continue

                    toc.append(TableOfContentsItem(title=title, id=id_attr, level=level))

        return toc

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
