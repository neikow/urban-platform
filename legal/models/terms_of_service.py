from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page, PanelPlaceholder
from django.utils.translation import gettext_lazy as _

from core.blocks import BlockTypes


class TermsOfServicePage(Page):
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

    content = StreamField(
        BlockTypes,
        blank=True,
        verbose_name=_("Terms of service body content"),
    )

    class Meta(Page.Meta):
        verbose_name = _("Terms of Service Page")
        verbose_name_plural = _("Terms of Service Pages")
