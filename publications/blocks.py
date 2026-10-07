"""Blocks of the publications index ("Actualités") page.

The page reuses the home page blocks around its list of publications, which
is a block too so editors choose what comes before and after it. A page has
exactly one list (``block_counts`` in the model).
"""

from django.utils.translation import gettext_lazy as _

from core.blocks import (
    BLOCK_TYPE_CALL_TO_ACTION_BUTTON,
    BLOCK_TYPE_CARDS,
    BLOCK_TYPE_FAQ,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_RICH_TEXT,
    BLOCK_TYPE_VERTICAL_SPACER,
    AugmentedRichTextBlock,
    BlockTypeList,
    CardListBlock,
    CTAButtonBlock,
    CustomImageBlock,
    FAQBlock,
    VerticalSpacerBlock,
)
from home.blocks import (
    GROUP_OTHER,
    IndexListBlock,
    JoinBlock,
    OpenProjectsBlock,
    ProjectsMapBlock,
    SectionBlock,
    UpcomingEventsBlock,
)

BLOCK_TYPE_PUBLICATION_LIST = "publication_list"


class PublicationListBlock(IndexListBlock):
    class Meta:
        label = _("List of publications")
        icon = "list-ul"
        template = "publications/blocks/publication_list.html"
        description = _(
            "Projects and events, with search and filters, and links to follow the news."
        )
        preview_value = {"label": "Publications", "title": "Dernières publications"}


PUBLICATION_INDEX_BLOCK_TYPES: BlockTypeList = [
    (BLOCK_TYPE_PUBLICATION_LIST, PublicationListBlock()),
    ("section", SectionBlock()),
    ("join", JoinBlock()),
    ("open_projects", OpenProjectsBlock()),
    ("upcoming_events", UpcomingEventsBlock()),
    ("projects_map", ProjectsMapBlock()),
    (BLOCK_TYPE_RICH_TEXT, AugmentedRichTextBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_IMAGE, CustomImageBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CARDS, CardListBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_FAQ, FAQBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_VERTICAL_SPACER, VerticalSpacerBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CALL_TO_ACTION_BUTTON, CTAButtonBlock(group=GROUP_OTHER)),
]
