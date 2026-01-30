from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import StreamField
from django.utils.translation import gettext_lazy as _

from core.blocks import BlockTypes


class HomePage(Page):
    max_count = 1
    parent_page_types: list[str] = []
    subpage_types: list[str] = ["legal.LegalIndexPage", "pedagogy.PedagogyIndexPage"]

    content = StreamField(
        BlockTypes,
        blank=True,
        verbose_name=_("Home page content"),
        help_text=_("The main content of the home page."),
    )

    content_panels = Page.content_panels + [
        FieldPanel("content"),
    ]

    search_fields = []

    @classmethod
    def can_create_at(cls, parent: Page) -> bool:
        return False

    class Meta:
        verbose_name = _("Page d'accueil")
        verbose_name_plural = _("Pages d'accueil")
