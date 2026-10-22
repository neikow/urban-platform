"""Import an archive produced by ``export_content``.

    python manage.py import_content content.zip [--mode replace|create]

``replace`` (default) updates the pages and media that exist; ``create``
changes nothing that exists and adds the pages anew. The signature is required
when CONTENT_TRANSFER_KEY is set. See core.content_transfer.
"""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.content_transfer.archive import ArchiveError
from core.content_transfer.importer import ImportMode, import_archive


class Command(BaseCommand):
    help = "Import publications, pedagogy cards, the home page and media from a .zip archive."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archive", help="Path to the .zip archive to import.")
        parser.add_argument("--mode", choices=ImportMode.values, default=ImportMode.REPLACE)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            counts = import_archive(
                options["archive"],
                mode=options["mode"],
                key=settings.CONTENT_TRANSFER_KEY,
                log=lambda message: self.stdout.write(self.style.WARNING(message)),
            )
        except ArchiveError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {counts['pages_created']} new and {counts['pages_updated']} updated "
                f"page(s); media: {counts['media_created']} created, {counts['media_updated']} "
                f"updated, {counts['media_kept']} kept."
            )
        )
