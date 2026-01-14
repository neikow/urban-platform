from wagtail.models import Page
from django.utils.translation import gettext_lazy as _


class HomePage(Page):
    max_count = 1  # Limit to a single instance
    parent_page_types = []  # Prevent creation under any other page

    @classmethod
    def can_create_at(cls, parent):
        return False

    class Meta:
        verbose_name = _("Page d'accueil")
        verbose_name_plural = _("Pages d'accueil")
