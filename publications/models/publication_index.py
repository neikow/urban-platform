from typing import Any

from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest
from django.template import Context
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


class PublicationIndexPage(Page):
    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = ["publications.ProjectPage", "publications.EventPage"]
    show_in_menus_default = True

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Publications Index")

    page_introduction = models.TextField(
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
        from publications.models.project import ProjectPage, ProjectCategory
        from publications.models.event import EventPage

        publication_type = request.GET.get("type", "all")

        if publication_type == "projects":
            publications = (
                ProjectPage.objects.live()
                .descendant_of(self)
                .order_by("-first_published_at")
            )
            category = request.GET.get("category")
            if category and category in [c.value for c in ProjectCategory]:
                publications = publications.filter(category=category)
        elif publication_type == "events":
            publications = (
                EventPage.objects.live()
                .descendant_of(self)
                .order_by("-event_date")
            )
        else:
            projects = list(
                ProjectPage.objects.live()
                .descendant_of(self)
                .order_by("-first_published_at")
            )
            events = list(
                EventPage.objects.live()
                .descendant_of(self)
                .order_by("-first_published_at")
            )
            publications = sorted(
                projects + events,
                key=lambda x: x.first_published_at or x.last_published_at,
                reverse=True,
            )

        search_query = request.GET.get("search", "")
        if search_query and publication_type != "all":
            publications = publications.filter(
                models.Q(title__icontains=search_query)
                | models.Q(description__icontains=search_query)
            )

        paginator = Paginator(publications, 12)
        page_number = request.GET.get("page")
        return paginator.get_page(page_number)

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
