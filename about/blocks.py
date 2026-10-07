from typing import Any

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from django.utils.translation import gettext_lazy as _

from core.blocks import (
    BLOCK_TYPE_CALL_TO_ACTION_BUTTON,
    BLOCK_TYPE_CARDS,
    BLOCK_TYPE_FAQ,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_RECENT_PUBLICATIONS,
    BlockTypeList,
    CardListBlock,
    CTAButtonBlock,
    CustomImageBlock,
    FAQBlock,
    RecentPublicationsBlock,
)
from home.blocks import (
    GROUP_LIVE,
    GROUP_OTHER,
    GROUP_SECTIONS,
    JoinBlock,
    OpenProjectsBlock,
    SectionBlock,
    UpcomingEventsBlock,
)


class UserBlock(blocks.StructBlock):
    """A block representing a single user/member card."""

    name = blocks.CharBlock(
        label=_("Name"),
        required=True,
        max_length=255,
    )
    image = ImageChooserBlock(
        label=_("Photo"),
        required=False,
    )
    role = blocks.CharBlock(
        label=_("Role"),
        required=False,
        max_length=255,
    )
    description = blocks.TextBlock(
        label=_("Description"),
        required=False,
    )
    facebook_url = blocks.URLBlock(
        label=_("Facebook Profile URL"),
        required=False,
    )

    class Meta:
        label = _("User")
        template = "about/blocks/user_block.html"
        icon = "user"


class UserListBlock(blocks.ListBlock):
    """A block that holds a list of UserBlocks."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(UserBlock(), **kwargs)

    class Meta:
        label = _("User List")
        template = "about/blocks/user_list_block.html"
        icon = "group"


class MemberBlock(blocks.StructBlock):
    """A block representing a single dev team member card."""

    name = blocks.CharBlock(
        label=_("Name"),
        required=True,
        max_length=255,
    )
    image = ImageChooserBlock(
        label=_("Photo"),
        required=False,
    )
    role = blocks.CharBlock(
        label=_("Role"),
        required=False,
        max_length=255,
    )
    description = blocks.TextBlock(
        label=_("Description"),
        required=False,
    )
    github_url = blocks.URLBlock(
        label=_("GitHub Profile URL"),
        required=False,
    )
    facebook_url = blocks.URLBlock(
        label=_("Facebook Profile URL"),
        required=False,
    )
    personal_website_url = blocks.URLBlock(
        label=_("Personal Website URL"),
        required=False,
    )

    class Meta:
        label = _("Member")
        template = "about/blocks/member_block.html"
        icon = "user"


class MembersListBlock(blocks.ListBlock):
    """A block that holds a list of MemberBlocks (dev team)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(MemberBlock(), **kwargs)

    class Meta:
        label = _("Members List")
        template = "about/blocks/members_list_block.html"
        icon = "group"


# --- The content of the "À propos" pages -------------------------------------------
# The home page blocks, plus a text block in the reading width the pages had
# before they had blocks. The members stay in their own field, shown after.

ABOUT_TEXT_FEATURES = ["h2", "h3", "bold", "italic", "link", "ol", "ul", "document-link"]


class AboutTextBlock(blocks.RichTextBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(features=ABOUT_TEXT_FEATURES, **kwargs)

    class Meta:
        label = _("Text")
        icon = "pilcrow"
        template = "about/blocks/text.html"
        group = GROUP_SECTIONS
        description = _("Text in the reading width, with headings, lists and links.")


ABOUT_BLOCK_TYPES: BlockTypeList = [
    ("text", AboutTextBlock()),
    ("section", SectionBlock()),
    ("join", JoinBlock()),
    ("open_projects", OpenProjectsBlock()),
    ("upcoming_events", UpcomingEventsBlock()),
    (BLOCK_TYPE_RECENT_PUBLICATIONS, RecentPublicationsBlock(group=GROUP_LIVE)),
    (BLOCK_TYPE_IMAGE, CustomImageBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CARDS, CardListBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_FAQ, FAQBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CALL_TO_ACTION_BUTTON, CTAButtonBlock(group=GROUP_OTHER)),
]
