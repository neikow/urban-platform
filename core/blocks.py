from typing import Any

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


class HeroBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    subtitle = blocks.TextBlock(required=False)
    image = ImageChooserBlock()
    alt_text = blocks.CharBlock(required=True, max_length=255)
    cta_link = blocks.URLBlock(required=False)
    cta_text = blocks.CharBlock(required=False)

    class Meta:
        template = "core/blocks/hero_block.html"
        icon = "image"


class CardBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    description = blocks.TextBlock(required=True)
    image = ImageChooserBlock(required=False)
    alt_text = blocks.CharBlock(required=False, max_length=255)
    link = blocks.URLBlock(required=False)

    class Meta:
        template = "core/blocks/card_block.html"
        icon = "placeholder"


class CardListBlock(blocks.ListBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(CardBlock(), **kwargs)

    class Meta:
        template = "core/blocks/card_list_block.html"
        icon = "list-ul"


class TestimonialBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True)
    author_name = blocks.CharBlock(required=True)
    author_title = blocks.CharBlock(required=False)
    author_image = ImageChooserBlock(required=False)

    class Meta:
        template = "core/blocks/testimonial_block.html"
        icon = "user"


class RecentPublicationsBlock(blocks.StructBlock):
    number_of_publications = blocks.IntegerBlock(
        default=5,
        min_value=1,
        max_value=20,
        label=_("Number of Publications"),
        required=True,
    )

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        context = super().get_context(value, parent_context=parent_context)

        from publications.models import PublicationPage

        context["publications"] = (
            PublicationPage.objects.live()
            .public()
            .order_by("-first_published_at")[: value["number_of_publications"]]
        )
        return context

    class Meta:
        template = "core/blocks/recent_publications_block.html"
        icon = "doc-full"


class FAQQuestionBlock(blocks.StructBlock):
    question = blocks.CharBlock(required=True)
    answer = blocks.TextBlock(required=True)

    class Meta:
        template = "core/blocks/faq_block.html"
        icon = "help"


class FAQBlock(blocks.ListBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(FAQQuestionBlock(), **kwargs)

    class Meta:
        template = "core/blocks/faq_list_block.html"
        icon = "help"


BLOCK_TYPE_TEXT = "text"
BLOCK_TYPE_IMAGE = "image"
BLOCK_TYPE_IMAGE_TEXT = "image_text"
BLOCK_TYPE_TEXT_CENTERED = "text_centered"
BLOCK_TYPE_HERO = "hero"
BLOCK_TYPE_CARDS = "cards"
BLOCK_TYPE_TESTIMONIAL = "testimonial"
BLOCK_TYPE_RECENT_PUBLICATIONS = "recent_publications"
BLOCK_TYPE_FAQ = "faq"

BlockTypes: list[tuple[str, blocks.Block]] = [
    (
        BLOCK_TYPE_TEXT,
        blocks.RichTextBlock(
            features=[
                "h2",
                "h3",
                "h4",
                "bold",
                "italic",
                "link",
                "document-link",
                "ul",
                "ol",
                "blockquote",
                "superscript",
                "subscript",
            ],
            label=_("Text"),
            template="core/blocks/rich_text_block.html",
        ),
    ),
    (
        BLOCK_TYPE_TEXT_CENTERED,
        blocks.RichTextBlock(
            features=[
                "bold",
                "italic",
            ],
            label=_("Centered Text"),
            template="core/blocks/centered_text_block.html",
        ),
    ),
    (BLOCK_TYPE_IMAGE, ImageBlock(label=_("Image"), template="core/blocks/image_block.html")),
    (
        BLOCK_TYPE_IMAGE_TEXT,
        ImageTextBlock(label=_("Image & Text Row"), template="core/blocks/image_text_block.html"),
    ),
    (BLOCK_TYPE_HERO, HeroBlock(label=_("Hero Block"))),
    (BLOCK_TYPE_CARDS, CardListBlock(label=_("Card List Block"))),
    (BLOCK_TYPE_TESTIMONIAL, TestimonialBlock(label=_("Testimonial Block"))),
    (BLOCK_TYPE_RECENT_PUBLICATIONS, RecentPublicationsBlock(label=_("Recent Publications Block"))),
    (BLOCK_TYPE_FAQ, FAQBlock(label=_("FAQ Block"))),
]
