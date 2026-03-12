from typing import Any

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from django.utils.translation import gettext_lazy as _


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
