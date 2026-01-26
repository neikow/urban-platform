from typing import Any

from django.db import models
from django.http import HttpRequest
from django.template import Context
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from publications.services import PublicationFilters, get_filtered_publications


class PublicationIndexPage(Page):
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

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Context:
        from publications.models.project import ProjectCategory

        context = super().get_context(request, *args, **kwargs)
        context["publications"] = self.get_publications(request)
        context["categories"] = ProjectCategory.choices
        context["selected_category"] = request.GET.get("category", "")
        context["selected_type"] = request.GET.get("type", "all")
        return context

    class Meta:
        verbose_name = verbose_name_plural = _("Publications Index")
