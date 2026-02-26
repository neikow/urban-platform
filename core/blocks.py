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
        label=_("Image Position"),
        choices=ImagePosition.choices,
        default=ImagePosition.LEFT,
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
        label=_("Image Alt Text (For accessibility, SEO, and in case the image fails to load)"),
        required=True,
        max_length=255,
    )


class HeroBlock(blocks.StructBlock):
    title = blocks.CharBlock(label=_("Title"), required=True)
    subtitle = blocks.TextBlock(label=_("Subtitle (Optional)"), required=False)
    image = ImageChooserBlock(
        label=_("Background Image"),
    )
    alt_text = blocks.CharBlock(
        label=_("Image Alt Text (For accessibility, SEO, and in case the image fails to load)"),
        required=True,
        max_length=255,
    )
    cta_link = blocks.URLBlock(
        label=_("Call-to-Action Link (Leave blank if no CTA button)"), required=False
    )
    cta_text = blocks.CharBlock(
        label=_("Call-to-Action Text (Leave blank if no CTA button)"), required=False
    )

    class Meta:
        template = "core/blocks/hero_block.html"
        icon = "image"


class CardBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        label=_("Card Title"),
        required=True,
        max_length=255,
    )
    description = blocks.TextBlock(
        label=_("Card Description"),
        required=True,
    )
    image = ImageChooserBlock(label=_("Card Image (Optional)"), required=False)
    alt_text = blocks.CharBlock(
        label=_(
            "Card Image Alt Text (For accessibility, SEO, and in case the image fails to load)"
        ),
        required=False,
        max_length=255,
    )
    link = blocks.URLBlock(
        required=False,
        label=_("Card Link (Optional)"),
    )

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
    quote = blocks.TextBlock(label=_("Testimonial Quote"), required=True)
    author_name = blocks.CharBlock(label=_("Author Name"), required=True)
    author_title = blocks.CharBlock(label=_("Author Title (Optional)"), required=False)
    author_image = ImageChooserBlock(label=_("Author Image (Optional)"), required=False)

    class Meta:
        template = "core/blocks/testimonial_block.html"
        icon = "user"


class RecentPublicationsBlock(blocks.StructBlock):
    number_of_publications = blocks.IntegerBlock(
        label=_("Number of Publications"),
        default=5,
        min_value=1,
        max_value=20,
        required=True,
    )

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        context = super().get_context(value, parent_context=parent_context)

        from publications.models import PublicationPage

        # TODO: URB-148 Add caching to this query to avoid hitting the database on every page load
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
    question = blocks.CharBlock(label=_("Question"), required=True)
    answer = blocks.TextBlock(label=_("Answer"), required=True)

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
DEPRECATED_BLOCK_TYPE_IMAGE_TEXT = "image_text"
DEPRECATED_BLOCK_TYPE_TEXT_CENTERED = "text_centered"
BLOCK_TYPE_HERO = "hero"
BLOCK_TYPE_CARDS = "cards"
BLOCK_TYPE_TESTIMONIAL = "testimonial"
BLOCK_TYPE_RECENT_PUBLICATIONS = "recent_publications"
BLOCK_TYPE_FAQ = "faq"

COMMON_BLOCK_TYPES: list[tuple[str, blocks.Block]] = [
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
        DEPRECATED_BLOCK_TYPE_TEXT_CENTERED,
        blocks.RichTextBlock(
            features=[
                "bold",
                "italic",
            ],
            label=_("DEPRECATED Centered Text"),
            template="core/blocks/centered_text_block.html",
        ),
    ),
    (BLOCK_TYPE_IMAGE, ImageBlock(label=_("Image"), template="core/blocks/image_block.html")),
    (
        DEPRECATED_BLOCK_TYPE_IMAGE_TEXT,
        ImageTextBlock(
            label=_("DEPRECATED Image & Text Row"), template="core/blocks/image_text_block.html"
        ),
    ),
    (BLOCK_TYPE_FAQ, FAQBlock(label=_("FAQ Block"))),
]

CONTENT_BLOCK_TYPES = COMMON_BLOCK_TYPES + []

WEBSITE_BLOCK_TYPES = COMMON_BLOCK_TYPES + [
    (BLOCK_TYPE_HERO, HeroBlock(label=_("Hero Block"))),
    (BLOCK_TYPE_TESTIMONIAL, TestimonialBlock(label=_("Testimonial Block"))),
    (BLOCK_TYPE_RECENT_PUBLICATIONS, RecentPublicationsBlock(label=_("Recent Publications Block"))),
    (BLOCK_TYPE_CARDS, CardListBlock(label=_("Card List Block"))),
]
