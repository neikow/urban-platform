from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from django.utils.translation import gettext_lazy as _


class AboutIndexPage(Page):
    max_count_per_parent = 1
    parent_page_types: list[str] = ["home.HomePage"]
    child_page_types: list[str] = [
        "about.AboutWebsitePage",
        "about.AboutCommissionPage",
        "about.AboutDevTeamPage",
    ]
    show_in_menus_default = False
    is_creatable = False
    content_panels: list = []

    class Meta(Page.Meta):
        verbose_name = _("About Index Page")
        verbose_name_plural = _("About Index Pages")
