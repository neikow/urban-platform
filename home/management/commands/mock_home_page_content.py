from typing import Any

from django.core.management import BaseCommand
from core.blocks import (
    BLOCK_TYPE_HERO,
    BLOCK_TYPE_IMAGE_TEXT,
    BLOCK_TYPE_CARDS,
    BLOCK_TYPE_TESTIMONIAL,
    BLOCK_TYPE_RECENT_PUBLICATIONS,
    BLOCK_TYPE_FAQ,
    BLOCK_TYPE_TEXT_CENTERED,
)
from core.tests.utils.blocks import mock_block_value
from home.models import HomePage


class Command(BaseCommand):
    help = "Create mock home page content."

    def handle(self, *args: Any, **options: Any) -> None:
        home_page: HomePage | None = HomePage.objects.first()

        if not home_page:
            self.stderr.write(
                self.style.ERROR(
                    "No HomePage found. Please ensure a HomePage exists in the database."
                )
            )
            return

        home_page.content = [
            (BLOCK_TYPE_HERO, mock_block_value(BLOCK_TYPE_HERO)),
            (BLOCK_TYPE_TEXT_CENTERED, mock_block_value(BLOCK_TYPE_TEXT_CENTERED)),
            (BLOCK_TYPE_IMAGE_TEXT, mock_block_value(BLOCK_TYPE_IMAGE_TEXT)),
            (BLOCK_TYPE_CARDS, mock_block_value(BLOCK_TYPE_CARDS)),
            (BLOCK_TYPE_TEXT_CENTERED, mock_block_value(BLOCK_TYPE_TEXT_CENTERED)),
            (BLOCK_TYPE_TESTIMONIAL, mock_block_value(BLOCK_TYPE_TESTIMONIAL)),
            (BLOCK_TYPE_TESTIMONIAL, mock_block_value(BLOCK_TYPE_TESTIMONIAL)),
            (BLOCK_TYPE_RECENT_PUBLICATIONS, mock_block_value(BLOCK_TYPE_RECENT_PUBLICATIONS)),
            (BLOCK_TYPE_TEXT_CENTERED, mock_block_value(BLOCK_TYPE_TEXT_CENTERED)),
            (BLOCK_TYPE_FAQ, mock_block_value(BLOCK_TYPE_FAQ)),
        ]

        home_page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS("Mock home page content created successfully."))
