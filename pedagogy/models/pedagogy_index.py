from django.core.paginator import Paginator
from django.db import models
from wagtail.fields import RichTextField
from wagtail.models import Page
from django.utils.translation import gettext_lazy as _
from wagtail.search import index
from wagtail.admin.panels import FieldPanel
from pedagogy.models.pedagogy_card import PedagogyCardPage


class PedagogyIndexPage(Page):
    max_count = 1
    parent_page_types = ["home.HomePage"]

    page_introduction = models.TextField(
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
        index.SearchField("page_introduction"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("page_introduction"),
        FieldPanel("body"),
    ]

    @classmethod
    def get_verbose_name(cls):
        return _("Pedagogy Entries Index")

    def _populate_pedagogy_entries(self, context, request):
        pedagogy_entries = (
            PedagogyCardPage.objects.live()
            .descendant_of(self)
            .order_by("-first_published_at")
        )
        search_query = request.GET.get("search", "")
        if search_query:
            pedagogy_entries = pedagogy_entries.filter(
                models.Q(title__icontains=search_query)
                | models.Q(description__icontains=search_query)
                | models.Q(body__icontains=search_query)
            )

        paginator = Paginator(pedagogy_entries, 9)
        page_number = request.GET.get("page")
        pedagogy_entries = paginator.get_page(page_number)

        context.update({"pedagogy_entries": pedagogy_entries})

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        self._populate_pedagogy_entries(context, request)
        return context

    class Meta:
        verbose_name = verbose_name_plural = _("Pedagogy Entries Index")
