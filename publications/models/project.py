from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel
from wagtail.search import index

from core.toc import TableOfContentsItem, generate_header_ids, get_table_of_contents
from publications.models.publication import PublicationPage


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

    @property
    def is_project(self) -> bool:
        return True

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
                generate_header_ids(block)

    @property
    def table_of_contents(self) -> list[TableOfContentsItem]:
        return get_table_of_contents(self.content)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
