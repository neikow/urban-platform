import random
from typing import Any

from core.tests.utils.faker_shortcuts import title, paragraph, sentence
from pedagogy.factories.image_factory import ImageFactory
from pedagogy.factories.document_factory import DocumentFactory
from core.blocks import ImagePosition


def mock_block_value(block_type: str) -> Any:
    if block_type == "text":
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
                  </ul
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

    elif block_type == "image":
        image = ImageFactory.create()

        return {
            "image": image,
            "alt_text": image.title,
        }

    elif block_type == "image_text":
        image = ImageFactory.create()
        position = random.choice(ImagePosition.values)

        return {
            "paragraph": paragraph(12),
            "image": image,
            "alt_text": image.title,
            "position": position,
        }

    else:
        raise ValueError(f"Unsupported block type: {block_type}")
