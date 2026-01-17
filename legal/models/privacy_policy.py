from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page, PanelPlaceholder
from django.utils.translation import gettext_lazy as _


class PrivacyPolicyPage(Page):
    is_creatable = False
    max_count_per_parent = 1
    parent_page_types: list[str] = ["legal.LegalIndexPage"]
    child_page_types: list[str] = []

    content_panels = Page.content_panels + [
        FieldPanel("content"),
    ]

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

    content = RichTextField(
        features=["h2", "h3", "bold", "italic", "link", "ol", "ul", "document-link"],
        blank=True,
        verbose_name=_("Privacy policy body content"),
    )

    class Meta(Page.Meta):
        verbose_name = _("Privacy Policy Page")
        verbose_name_plural = _("Privacy Policy Pages")
