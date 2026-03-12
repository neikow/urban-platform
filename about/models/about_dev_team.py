from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from django.utils.translation import gettext_lazy as _

from about.blocks import MembersListBlock


class AboutDevTeamPage(Page):
    is_creatable = False
    max_count_per_parent = 1
    parent_page_types: list[str] = ["about.AboutIndexPage"]
    child_page_types: list[str] = []

    content = RichTextField(
        features=["h2", "h3", "bold", "italic", "link", "ol", "ul", "document-link"],
        blank=True,
        verbose_name=_("Content"),
    )

    members = StreamField(
        [("members_list", MembersListBlock())],
        blank=True,
        verbose_name=_("Dev Team Members"),
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("content"),
        FieldPanel("members"),
    ]

    class Meta(Page.Meta):
        verbose_name = _("About Dev Team Page")
        verbose_name_plural = _("About Dev Team Pages")
