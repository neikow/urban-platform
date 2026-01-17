from wagtail.models import Page
from django.utils.translation import gettext_lazy as _


class HomePage(Page):
    max_count = 1
    parent_page_types: list[str] = []
    subpage_types: list[str] = ["legal.LegalIndexPage", "pedagogy.PedagogyIndexPage"]

    @classmethod
    def can_create_at(cls, parent: Page) -> bool:
        return False

    class Meta:
        verbose_name = _("Page d'accueil")
        verbose_name_plural = _("Pages d'accueil")
