from wagtail.models import Page, PanelPlaceholder
from django.utils.translation import gettext_lazy as _


class LegalIndexPage(Page):
    max_count_per_parent = 1
    parent_page_types: list[str] = ["home.HomePage"]
    child_page_types: list[str] = []
    show_in_menus_default = False
    is_creatable = False
    content_panels: list = []
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

    class Meta(Page.Meta):
        verbose_name = _("Legal Index Page")
        verbose_name_plural = _("Legal Index Pages")
