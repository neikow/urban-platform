from wagtail import blocks
from wagtail.images.blocks import ImageBlock, ImageChooserBlock
from django.db import models
from django.utils.translation import gettext_lazy as _


class ImagePosition(models.TextChoices):
    LEFT = "left", _("Left")
    RIGHT = "right", _("Right")


class ImageTextBlock(blocks.StructBlock):
    position = blocks.ChoiceBlock(
        choices=ImagePosition.choices,
        default=ImagePosition.LEFT,
        label=_("Image Position"),
        required=True,
    )
    paragraph = blocks.TextBlock(
        label=_("Text"),
        required=True,
    )
    image = ImageChooserBlock(
        label=_("Image"),
        required=True,
    )
    alt_text = blocks.CharBlock(
        required=True,
        max_length=255,
        label=_("Alt Text"),
    )


BlockTypes: list[tuple[str, blocks.Block]] = [
    (
        "text",
        blocks.RichTextBlock(
            label=_("Text"), template="core/blocks/rich_text_block.html"
        ),
    ),
    ("image", ImageBlock(label=_("Image"), template="core/blocks/image_block.html")),
    (
        "image_text",
        ImageTextBlock(
            label=_("Image & Text Row"), template="core/blocks/image_text_block.html"
        ),
    ),
]
