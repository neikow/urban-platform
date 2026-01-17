from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page, PanelPlaceholder
from wagtail.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from wagtail.search import index


class PedagogyCardPage(Page):
    parent_page_types: list[str] = ["pedagogy.PedagogyIndexPage"]
    child_page_types: list[str] = []

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

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Pedagogy Card")

    body = RichTextField(
        blank=True,
        verbose_name=_("Card body content"),
        help_text=_("The main content of the pedagogy card."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
