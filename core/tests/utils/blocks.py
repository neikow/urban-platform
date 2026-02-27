import random
from typing import Any

from core.tests.utils.faker_shortcuts import title, paragraph
from core.tests.utils.factories import ImageFactory, DocumentFactory
from core.blocks import (
    DEPRECATED_BLOCK_TYPE_TEXT,
    BLOCK_TYPE_IMAGE,
    DEPRECATED_BLOCK_TYPE_IMAGE_TEXT,
    BLOCK_TYPE_HERO,
    BLOCK_TYPE_CARDS,
    DEPRECATED_BLOCK_TYPE_TESTIMONIAL,
    BLOCK_TYPE_RECENT_PUBLICATIONS,
    BLOCK_TYPE_FAQ,
    DEPRECATED_BLOCK_TYPE_TEXT_CENTERED,
    BLOCK_TYPE_TESTIMONIAL_LIST,
    BLOCK_TYPE_TWO_COLUMN,
    BLOCK_TYPES_AVAILABLE_IN_TWO_COLUMNS,
    BLOCK_TYPE_RICH_TEXT,
    TextJustification,
    ImageSize,
    BLOCK_TYPE_VERTICAL_SPACER,
    BLOCK_TYPE_CALL_TO_ACTION_BUTTON,
    ButtonStyle,
    ButtonAlignment,
    BLOCK_TYPE_DOCUMENT,
)


def deprecated_block_error(block_type: str) -> RuntimeError:
    return RuntimeError(f"{block_type} is deprecated and should not be used in new tests.")


def mock_block_value(block_type: str) -> Any:
    if block_type == DEPRECATED_BLOCK_TYPE_TEXT:
        raise deprecated_block_error(block_type)

    elif block_type == DEPRECATED_BLOCK_TYPE_TEXT_CENTERED:
        raise deprecated_block_error(block_type)

    elif block_type == BLOCK_TYPE_IMAGE:
        image = ImageFactory.create()

        return {
            "image": image,
            "size": random.choice(ImageSize.values),
            "alt_text": image.title,
        }

    elif block_type == DEPRECATED_BLOCK_TYPE_IMAGE_TEXT:
        raise deprecated_block_error(block_type)

    elif block_type == BLOCK_TYPE_HERO:
        image = ImageFactory.create()

        return {
            "title": title(6),
            "subtitle": paragraph(4),
            "image": image,
            "alt_text": image.title,
            "cta_link": "https://example.com",
            "cta_text": "Click Here",
        }

    elif block_type == BLOCK_TYPE_CARDS:
        return [
            {
                "title": title(5),
                "description": paragraph(6),
                "image": ImageFactory.create(),
                "alt_text": title(3),
                "link": "https://example.com",
            },
            {
                "title": title(5),
                "description": paragraph(6),
                "image": ImageFactory.create(),
                "alt_text": title(3),
                "link": "https://example.com",
            },
            {
                "title": title(5),
                "description": paragraph(6),
                "image": ImageFactory.create(),
                "alt_text": title(3),
                "link": "https://example.com",
            },
        ]

    elif block_type == BLOCK_TYPE_TWO_COLUMN:
        left_content_type = random.choice(BLOCK_TYPES_AVAILABLE_IN_TWO_COLUMNS)[0]
        right_content_type = random.choice(BLOCK_TYPES_AVAILABLE_IN_TWO_COLUMNS)[0]
        return {
            "left_column": [
                (left_content_type, mock_block_value(left_content_type)),
            ],
            "right_column": [
                (right_content_type, mock_block_value(right_content_type)),
            ],
        }

    elif block_type == DEPRECATED_BLOCK_TYPE_TESTIMONIAL:
        raise deprecated_block_error(block_type)

    elif block_type == BLOCK_TYPE_TESTIMONIAL_LIST:
        return [
            {
                "quote": paragraph(8),
                "author_name": title(2),
                "author_title": title(3),
                "author_image": ImageFactory.create(),
            },
            {
                "quote": paragraph(3),
                "author_name": title(2),
                "author_title": title(3),
                "author_image": ImageFactory.create(),
            },
        ]

    elif block_type == BLOCK_TYPE_RICH_TEXT:
        return {
            "justification": random.choice(TextJustification.values),
            "text": "<p>" + paragraph(10) + "</p>",
        }

    elif block_type == BLOCK_TYPE_RECENT_PUBLICATIONS:
        return {
            "number_of_publications": 5,
        }

    elif block_type == BLOCK_TYPE_FAQ:
        return [
            {
                "question": title(6),
                "answer": paragraph(10),
            },
            {
                "question": title(6),
                "answer": paragraph(10),
            },
        ]

    elif block_type == BLOCK_TYPE_VERTICAL_SPACER:
        return {
            "height": random.randint(10, 100),
            "hide_on_mobile": random.choice([True, False]),
        }

    elif block_type == BLOCK_TYPE_CALL_TO_ACTION_BUTTON:
        return {
            "text": title(3),
            "url": "https://example.com",
            "style": random.choice(ButtonStyle.values),
            "alignment": random.choice(ButtonAlignment.values),
        }

    elif block_type == BLOCK_TYPE_DOCUMENT:
        document = DocumentFactory.create()

        return {
            "document": document,
            "text": title(5),
            "style": random.choice(ButtonStyle.values),
            "alignment": random.choice(ButtonAlignment.values),
        }

    else:
        raise NotImplementedError(f"Unsupported block type: {block_type}")
