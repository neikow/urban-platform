from typing import Any
from django_stubs_ext import StrOrPromise

from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.template import Context
from django.template.response import TemplateResponse
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import StreamField
from wagtail.models import Page, PanelPlaceholder
from django.utils.translation import gettext_lazy as _
from wagtail.search import index
from wagtail.admin.panels import FieldPanel
from pedagogy.blocks import BLOCK_TYPE_CARD_LIST, PEDAGOGY_INDEX_BLOCK_TYPES
from pedagogy.models.pedagogy_card import PedagogyCardPage


def default_content() -> list[dict[str, Any]]:
    return [{"type": BLOCK_TYPE_CARD_LIST, "value": {"label": "", "title": ""}}]


class PedagogyIndexPage(RoutablePageMixin, Page):
    PEDAGOGY_ENTRIES_PER_PAGE = 9

    max_count = 1
    parent_page_types = ["home.HomePage"]
    page_templates = "pedagogy.page_templates.INDEX_TEMPLATES"

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
    content = StreamField(
        PEDAGOGY_INDEX_BLOCK_TYPES,
        block_counts={BLOCK_TYPE_CARD_LIST: {"min_num": 1, "max_num": 1}},
        default=default_content,
        verbose_name=_("Page content"),
        help_text=_("The list of cards and the parts around it."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("page_introduction"),
        index.SearchField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("page_introduction"),
        FieldPanel("content"),
    ]

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Pedagogy Entries Index")

    def get_results_context(self, request: HttpRequest) -> dict[str, Any]:
        """What the list region (components/pedagogy_results.html) needs."""
        pedagogy_entries = (
            PedagogyCardPage.objects.live().descendant_of(self).order_by("-first_published_at")
        )
        search_query = request.GET.get("search", "")
        if search_query:
            pedagogy_entries = pedagogy_entries.filter(
                models.Q(title__icontains=search_query)
                | models.Q(description__icontains=search_query)
                | models.Q(content__icontains=search_query)
            )

        paginator = Paginator(pedagogy_entries, self.PEDAGOGY_ENTRIES_PER_PAGE)
        page_number = request.GET.get("page")
        pedagogy_entries = paginator.get_page(page_number)

        return {"pedagogy_entries": pedagogy_entries}

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Context:
        context = super().get_context(request, *args, **kwargs)
        context.update(self.get_results_context(request))
        return context

    @path("results/", name="results")
    def results(self, request: HttpRequest) -> HttpResponse:
        """The list region alone, fetched by lib/instant-results.ts."""
        response = TemplateResponse(
            request,
            "pedagogy/components/pedagogy_results.html",
            {"page": self, "request": request, **self.get_results_context(request)},
        )
        response["X-Robots-Tag"] = "noindex"
        return response

    class Meta:
        verbose_name = verbose_name_plural = _("Pedagogy Entries Index")
