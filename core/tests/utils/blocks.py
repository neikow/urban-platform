import random
from typing import Any

from core.tests.utils.faker_shortcuts import title, paragraph, sentence
from core.tests.utils.factories import ImageFactory, DocumentFactory
from core.blocks import (
    ImagePosition,
    BLOCK_TYPE_TEXT,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_IMAGE_TEXT,
    BLOCK_TYPE_HERO,
    BLOCK_TYPE_CARDS,
    BLOCK_TYPE_TESTIMONIAL,
    BLOCK_TYPE_RECENT_PUBLICATIONS,
    BLOCK_TYPE_FAQ,
    BLOCK_TYPE_TEXT_CENTERED,
)


def mock_block_value(block_type: str) -> Any:
    if block_type == BLOCK_TYPE_TEXT:
        document = DocumentFactory.create()

        return f"""
          <h2>{title(4)}</h2>
          <p>{paragraph(5)}</p>

          <p>
          <ul>
            <li>{sentence(8)}</li>
            <li>{sentence(4)}</li>
            <li>
              <ul>
                <li>{sentence(6)}</li>
                <li>{sentence(7)}</li>
                <li>
                  <ul>
                    <li>{sentence(3)}</li>
                    <li>{sentence(9)}</li>
                  </ul>
                </li>
              </ul>
            </li>
            <li>{sentence(5)}</li>
          </ul>
          </p>

          <p>
            <ol>
              <li>{sentence(10)}</li>
              <li>{sentence(6)}</li>
              <li>{sentence(8)}</li>
              <li>
                <ol>
                  <li>{sentence(7)}</li>
                  <li>{sentence(4)}</li>
                  <li>
                    <ol>
                      <li>{sentence(5)}</li>
                      <li>{sentence(9)}</li>
                    </ol>
                  </li>
                </ol>
              </li>
            </ol>
          </p>

          <p>
            <a href="https://google.com">Link to Google</a>
          </p>

          <p>
            <a linktype="document" id="{document.id}">{document.title}</a>
          </p>

          <blockquote>{paragraph(3)}</blockquote>

          <p>
            <i>{paragraph(2)}</i>
          </p>
          <p>
            <b>{paragraph(2)}</b>
          </p>

          <p>E = mc<sup>2</sup></p>

          <p>H<sub>2</sub>O is water.</p>

          <h3>{paragraph(1)}</h3>
          <p>{paragraph(20)}</p>
          <h3>{paragraph(1)}</h3>
          <p>{paragraph(15)}</p>
          <h4>{paragraph(1)}</h4>
          <p>{paragraph(10)}</p>
          <h4>{paragraph(1)}</h4>
          <p>{paragraph(8)}</p>
          <h3>{paragraph(1)}</h3>
          <p>{paragraph(12)}</p>

       """

    elif block_type == BLOCK_TYPE_TEXT_CENTERED:
        return f"""
            <p>
                {paragraph(2)}
                <b>{paragraph(1)}</b>
                {paragraph(1)}
                <i>{paragraph(1)}</i>
                {paragraph(1)}
            </p>
        """

    elif block_type == BLOCK_TYPE_IMAGE:
        image = ImageFactory.create()

        return {
            "image": image,
            "alt_text": image.title,
        }

    elif block_type == BLOCK_TYPE_IMAGE_TEXT:
        image = ImageFactory.create()
        position = random.choice(ImagePosition.values)

        return {
            "paragraph": paragraph(12),
            "image": image,
            "alt_text": image.title,
            "position": position,
        }

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

    elif block_type == BLOCK_TYPE_TESTIMONIAL:
        return {
            "quote": paragraph(8),
            "author_name": title(2),
            "author_title": title(3),
            "author_image": ImageFactory.create(),
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

    else:
        raise ValueError(f"Unsupported block type: {block_type}")
