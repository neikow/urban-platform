from dataclasses import dataclass
from typing import Any

from django.db import models
from django.http import HttpRequest, HttpResponse
from django.template import Context
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from publications.geo import feature_collection, map_config
from publications.services import PublicationFilters, get_filtered_publications


@dataclass
class CategoryFilter:
    label: StrOrPromise
    value: str
    is_selected: bool


class PublicationIndexPage(RoutablePageMixin, Page):
    PUBLICATIONS_PER_PAGE = 12

    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = ["publications.ProjectPage", "publications.EventPage"]
    show_in_menus_default = True

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Publications Index")

    page_introduction: models.TextField[str, str] = models.TextField(
        blank=True,
        verbose_name=_("Page introduction"),
        help_text=_("Small introduction shown above the publications list."),
        default="Découvrez les projets et événements en cours et à venir dans votre quartier.",
    )

    body = RichTextField(
        blank=True,
        verbose_name=_("Page body content"),
        help_text=_("Additional content for the publications page."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("page_introduction"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("page_introduction"),
        FieldPanel("body"),
    ]

    def get_publications(self, request: HttpRequest) -> Any:
        from publications.models.publication import PublicationPage

        base_queryset = PublicationPage.objects.live().descendant_of(self)
        filters = PublicationFilters.from_request(request)

        return get_filtered_publications(
            base_queryset, filters, per_page=self.PUBLICATIONS_PER_PAGE
        )

    def get_projects_map(self) -> dict[str, Any]:
        """Located, published projects as GeoJSON for the "projects near me" map."""
        from publications.models.project import ProjectPage

        projects = (
            ProjectPage.objects.live()
            .public()
            .descendant_of(self)
            .filter(location__isnull=False)
            .order_by("-first_published_at")
        )
        return feature_collection(projects)

    def get_results_context(self, request: HttpRequest) -> dict[str, Any]:
        """What the list region (components/publication_results.html) needs."""
        from publications.models.project import ProjectCategory

        selected_category = request.GET.get("category", "")
        return {
            "publications": self.get_publications(request),
            "categories": [
                CategoryFilter(label=label, value=value, is_selected=(value == selected_category))
                for value, label in ProjectCategory.choices
            ],
            "selected_category": selected_category,
            "selected_type": request.GET.get("type", "all"),
            "show_past_events": request.GET.get("show_past", "").lower() in ("true", "1", "on"),
        }

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Context:
        context = super().get_context(request, *args, **kwargs)
        context.update(self.get_results_context(request))
        context["projects_map"] = self.get_projects_map()
        context["map_config"] = map_config()
        return context

    @path("results/", name="results")
    def results(self, request: HttpRequest) -> HttpResponse:
        """The list region alone, fetched by lib/instant-results.ts."""
        response = TemplateResponse(
            request,
            "publications/components/publication_results.html",
            {"page": self, "request": request, **self.get_results_context(request)},
        )
        response["X-Robots-Tag"] = "noindex"
        return response

    class Meta:
        verbose_name = verbose_name_plural = _("Publications Index")
