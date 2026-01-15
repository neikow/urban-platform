import random
from typing import Any

import faker

from core.blocks import ImagePosition


def mock_block_value(block_type: str) -> Any:
    from pedagogy.factories import ImageFactory

    if block_type == "text":
        return f"""
          <h2>{faker.Faker().paragraph(nb_sentences=1)}</h2>
          <p>{faker.Faker().paragraph(nb_sentences=5)}</p>
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
