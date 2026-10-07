"""Blocks of the pedagogy index ("Informations utiles") page.

Like the publications index: the home page blocks around the list of cards,
which is a block too. A page has exactly one list (``block_counts`` in the
model).
"""

from django.utils.translation import gettext_lazy as _

from core.blocks import (
    BLOCK_TYPE_CALL_TO_ACTION_BUTTON,
    BLOCK_TYPE_CARDS,
    BLOCK_TYPE_FAQ,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_RECENT_PUBLICATIONS,
    BLOCK_TYPE_RICH_TEXT,
    BLOCK_TYPE_VERTICAL_SPACER,
    AugmentedRichTextBlock,
    BlockTypeList,
    CardListBlock,
    CTAButtonBlock,
    CustomImageBlock,
    FAQBlock,
    RecentPublicationsBlock,
    VerticalSpacerBlock,
)
from home.blocks import (
    GROUP_LIVE,
    GROUP_OTHER,
    IndexListBlock,
    JoinBlock,
    OpenProjectsBlock,
    SectionBlock,
    UpcomingEventsBlock,
)

BLOCK_TYPE_CARD_LIST = "card_list"


class PedagogyCardListBlock(IndexListBlock):
    class Meta:
        label = _("List of cards")
        icon = "list-ul"
        template = "pedagogy/blocks/card_list.html"
        description = _("The useful information cards, with a search field.")
        preview_value = {"label": "Ressources", "title": "Dernières fiches"}


PEDAGOGY_INDEX_BLOCK_TYPES: BlockTypeList = [
    (BLOCK_TYPE_CARD_LIST, PedagogyCardListBlock()),
    ("section", SectionBlock()),
    ("join", JoinBlock()),
    ("open_projects", OpenProjectsBlock()),
    ("upcoming_events", UpcomingEventsBlock()),
    (BLOCK_TYPE_RECENT_PUBLICATIONS, RecentPublicationsBlock(group=GROUP_LIVE)),
    (BLOCK_TYPE_RICH_TEXT, AugmentedRichTextBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_IMAGE, CustomImageBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CARDS, CardListBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_FAQ, FAQBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_VERTICAL_SPACER, VerticalSpacerBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CALL_TO_ACTION_BUTTON, CTAButtonBlock(group=GROUP_OTHER)),
]
