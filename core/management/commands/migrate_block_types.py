import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page

# Import your specific page models here
# from publications.models import PublicationPage
# from home.models import HomePage
# from pedagogy.models import PedagogyCardPage


class Command(BaseCommand):
    help = "Migrates deprecated blocks to AugmentedRichTextBlock across specific models."

    def handle(self, *args: Any, **options: Any) -> None:
        from publications.models import PublicationPage
        from home.models import HomePage
        from pedagogy.models import PedagogyCardPage

        _models: list[tuple[type[Page], str]] = [
            (PublicationPage, "content"),
            (HomePage, "content"),
            (PedagogyCardPage, "content"),
        ]

        total_pages_migrated = 0

        for model_class, field_name in _models:
            pages = model_class.objects.all().specific()
            self.stdout.write(f"Checking {pages.count()} pages for {model_class.__name__}...")

            for page in pages:
                stream_field = getattr(page, field_name)

                # raw_data gives us the underlying JSON structure
                raw_data = stream_field.raw_data
                changed = False
                new_stream_data = []

                testimonials = []
                testimonial_list_block_index: int | None = None

                for block in raw_data:
                    block_type = block.get("type")
                    value = block.get("value")

                    if block_type == "text":
                        new_stream_data.append(
                            {
                                "type": "rich_text",
                                "value": {
                                    "justification": "left",
                                    "text": value,  # Old value was just the HTML string
                                },
                            }
                        )
                        changed = True

                    # Handle DEPRECATED_BLOCK_TYPE_TEXT_CENTERED -> BLOCK_TYPE_RICH_TEXT
                    elif block_type == "text_centered":
                        new_stream_data.append(
                            {
                                "type": "rich_text",
                                "value": {"justification": "center", "text": value},
                            }
                        )
                        changed = True

                    # Handle DEPRECATED_BLOCK_TYPE_IMAGE_TEXT -> Split into two blocks
                    elif block_type == "image_text":
                        image = value.get("image")
                        alt_text = value.get("alt_text", "")
                        text = value.get("paragraph", "")

                        image_on_left = value.get("position", "left") == "left"

                        image_block_data = {
                            "type": "image",
                            "value": {"image": image, "size": "full", "alt_text": alt_text},
                        }
                        text_block_data = {
                            "type": "rich_text",
                            "value": {
                                "justification": "left",
                                "text": f"<p>{text}</p>",
                            },
                        }

                        new_stream_data.append(
                            {
                                "type": "two_column",
                                "value": {
                                    "left_column": [
                                        image_block_data if image_on_left else text_block_data,
                                    ],
                                    "right_column": [
                                        text_block_data if image_on_left else image_block_data,
                                    ],
                                },
                            }
                        )

                        changed = True

                    elif block_type == "testimonial":
                        # Collect testimonials to convert into a single testimonial_list block
                        testimonials.append(value)
                        if testimonial_list_block_index is None:
                            # Insert a placeholder only once for the first testimonial
                            testimonial_list_block_index = len(new_stream_data)
                            new_stream_data.append(
                                {
                                    "type": "testimonial_list",
                                    "value": [],  # Placeholder, will be replaced later
                                }
                            )

                        changed = True

                    else:
                        # Keep existing valid blocks (FAQ, Hero, etc.) as they are
                        new_stream_data.append(block)

                if testimonials and testimonial_list_block_index is not None:
                    # Replace the placeholder testimonial_list block with the collected testimonials
                    new_stream_data[testimonial_list_block_index] = {
                        "type": "testimonial_list",
                        "value": testimonials,
                    }

                if changed:
                    # Update the field with the new JSON structure
                    setattr(page, field_name, json.dumps(new_stream_data))

                    with transaction.atomic():
                        # Save revision and publish to make changes live
                        revision = page.save_revision()
                        revision.publish()

                    self.stdout.write(f"  [MIGRATED] {page.title} ({page.id})")
                    total_pages_migrated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Migration complete. {total_pages_migrated} pages updated.")
        )
