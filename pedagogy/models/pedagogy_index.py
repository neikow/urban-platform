from typing import Any
from django_stubs_ext import StrOrPromise

from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest
from django.template import Context
from wagtail.fields import RichTextField
from wagtail.models import Page, PanelPlaceholder
from django.utils.translation import gettext_lazy as _
from wagtail.search import index
from wagtail.admin.panels import FieldPanel
from pedagogy.models.pedagogy_card import PedagogyCardPage


class PedagogyIndexPage(Page):
    max_count = 1
    parent_page_types = ["home.HomePage"]

    promote_panels = [
        PanelPlaceholder(
            "wagtail.admin.panels.MultiFieldPanel",
            [
                [
                    "seo_title",
                    "search_description",
                ],
                _("For search engines"),
            ],
            {},
        ),
    ]

    page_introduction: models.TextField = models.TextField(
        blank=True,
        verbose_name=_("Page introduction"),
        help_text=_("Small introduction shown above the pedagogy card list."),
        default="Voici un ensemble d'outils et de ressources pédagogiques pour vous aider à vous investir dans la vie de votre quartier.",
    )
    body = RichTextField(
        blank=True,
        verbose_name=_("Page body content"),
        help_text=_("Content for the pedagogy entries page."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("page_introduction"),
        FieldPanel("body"),
    ]

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Pedagogy Entries Index")

    def _populate_pedagogy_entries(
        self, context: Context, request: HttpRequest
    ) -> None:
        pedagogy_entries = (
            PedagogyCardPage.objects.live()
            .descendant_of(self)
            .order_by("-first_published_at")
        )
        paginator = Paginator(pedagogy_entries, 10)
        page_number = request.GET.get("page")
        pedagogy_entries = paginator.get_page(page_number)

        context.update({"pedagogy_entries": pedagogy_entries})

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Context:
        context = super().get_context(request, *args, **kwargs)
        self._populate_pedagogy_entries(context, request)
        return context

    class Meta:
        verbose_name = verbose_name_plural = _("Pedagogy Entries Index")
