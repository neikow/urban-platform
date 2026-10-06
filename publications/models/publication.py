from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from core.blocks import CONTENT_BLOCK_TYPES


class PublicationPage(Page):
    parent_page_types: list[str] = ["publications.PublicationIndexPage"]

    class Meta:
        verbose_name = _("Publication")
        verbose_name_plural = _("Publications")

    # Overridden by EventPage / ProjectPage. Querysets of publications are
    # turned into their specific type with `.specific()` before rendering.
    is_event = False
    is_project = False

    description: models.TextField[str, str] = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("A brief description shown in lists."),
    )

    hero_image: models.ForeignKey[Any, Any] = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Hero Image"),
        help_text=_("Main image for this publication"),
    )

    content = StreamField(
        CONTENT_BLOCK_TYPES,
        blank=True,
        verbose_name=_("Content"),
        help_text=_("The main content of the page."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("description"),
        index.SearchField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        FieldPanel("hero_image"),
        FieldPanel("content"),
    ]
