"""Export publications, pedagogy cards, the home page and their media to an archive.

    python manage.py export_content --output content.zip

Signed with CONTENT_TRANSFER_KEY when it is set. Load it elsewhere with
``import_content``, or from Settings › Content transfer. See core.content_transfer.
"""

from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from core.content_transfer.exporter import export_archive


class Command(BaseCommand):
    help = "Export publications, pedagogy cards, the home page and their media to a .zip archive."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--output",
            "-o",
            default=None,
            help="Path of the .zip archive to write (default: content-<timestamp>.zip).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        output = options["output"] or (
            f"content-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.zip"
        )
        counts = export_archive(
            output,
            key=settings.CONTENT_TRANSFER_KEY,
            log=lambda message: self.stdout.write(self.style.WARNING(message)),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {counts['pages']} page(s), {counts['images']} image(s) "
                f"and {counts['documents']} document(s) to {output}"
            )
        )
