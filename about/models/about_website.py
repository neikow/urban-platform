from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from django.utils.translation import gettext_lazy as _

from about.blocks import ABOUT_BLOCK_TYPES


class AboutWebsitePage(Page):
    is_creatable = False
    max_count_per_parent = 1
    parent_page_types: list[str] = ["about.AboutIndexPage"]
    child_page_types: list[str] = []
    page_templates = "about.page_templates.WEBSITE_TEMPLATES"

    content = StreamField(
        ABOUT_BLOCK_TYPES,
        blank=True,
        verbose_name=_("Content"),
    )

    content_panels = Page.content_panels + [FieldPanel("content")]

    class Meta(Page.Meta):
        verbose_name = _("About Website Page")
        verbose_name_plural = _("About Website Pages")
