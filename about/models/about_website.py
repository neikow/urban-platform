from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from django.utils.translation import gettext_lazy as _


class AboutWebsitePage(Page):
    is_creatable = False
    max_count_per_parent = 1
    parent_page_types: list[str] = ["about.AboutIndexPage"]
    child_page_types: list[str] = []

    content = RichTextField(
        features=["h2", "h3", "bold", "italic", "link", "ol", "ul", "document-link"],
        blank=True,
        verbose_name=_("Content"),
    )

    content_panels = Page.content_panels + [FieldPanel("content")]

    class Meta(Page.Meta):
        verbose_name = _("About Website Page")
        verbose_name_plural = _("About Website Pages")
