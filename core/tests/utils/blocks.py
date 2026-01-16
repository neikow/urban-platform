import random
from typing import Any

import faker

from core.blocks import ImagePosition


def mock_block_value(block_type: str) -> Any:
    from pedagogy.factories import ImageFactory, DocumentFactory

    if block_type == "text":
        document = DocumentFactory.create()

        return f"""
          <h2>{faker.Faker().paragraph(nb_sentences=1)}</h2>
          <p>{faker.Faker().paragraph(nb_sentences=5)}</p>

          <p>
          <ul>
            <li>{faker.Faker().sentence(nb_words=8)}</li>
            <li>{faker.Faker().sentence(nb_words=4)}</li>
            <li>
              <ul>
                <li>{faker.Faker().sentence(nb_words=6)}</li>
                <li>{faker.Faker().sentence(nb_words=7)}</li>
                <li>
                  <ul>
                    <li>{faker.Faker().sentence(nb_words=3)}</li>
                    <li>{faker.Faker().sentence(nb_words=9)}</li>
                  </ul
                </li>
              </ul>
            </li>
            <li>{faker.Faker().sentence(nb_words=5)}</li>
          </ul>
          </p>

          <p>
            <ol>
              <li>{faker.Faker().sentence(nb_words=10)}</li>
              <li>{faker.Faker().sentence(nb_words=6)}</li>
              <li>{faker.Faker().sentence(nb_words=8)}</li>
              <li>
                <ol>
                  <li>{faker.Faker().sentence(nb_words=7)}</li>
                  <li>{faker.Faker().sentence(nb_words=4)}</li>
                  <li>
                    <ol>
                      <li>{faker.Faker().sentence(nb_words=5)}</li>
                      <li>{faker.Faker().sentence(nb_words=9)}</li>
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

          <blockquote>{faker.Faker().paragraph(nb_sentences=3)}</blockquote>

          <p>
            <i>{faker.Faker().paragraph(nb_sentences=2)}</i>
          </p>
          <p>
            <b>{faker.Faker().paragraph(nb_sentences=2)}</b>
          </p>

          <p>E = mc<sup>2</sup></p>

          <p>H<sub>2</sub>O is water.</p>

          <h3>{faker.Faker().paragraph(nb_sentences=1)}</h3>
          <p>{faker.Faker().paragraph(nb_sentences=20)}</p>
          <h3>{faker.Faker().paragraph(nb_sentences=1)}</h3>
          <p>{faker.Faker().paragraph(nb_sentences=15)}</p>
          <h4>{faker.Faker().paragraph(nb_sentences=1)}</h4>
          <p>{faker.Faker().paragraph(nb_sentences=10)}</p>
          <h4>{faker.Faker().paragraph(nb_sentences=1)}</h4>
          <p>{faker.Faker().paragraph(nb_sentences=8)}</p>
          <h3>{faker.Faker().paragraph(nb_sentences=1)}</h3>
          <p>{faker.Faker().paragraph(nb_sentences=12)}</p>


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
            "paragraph": faker.Faker().paragraph(nb_sentences=12),
            "image": image,
            "alt_text": image.title,
            "position": position,
        }

    else:
        raise ValueError(f"Unsupported block type: {block_type}")
