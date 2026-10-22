"""Import the CIQ of one federation from a CSV copy of the Confédération's directory.

See core.association_import for the file and what an import does. The same
import is available in the admin: Settings › Neighborhood associations › Import.
"""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.association_import import AssociationImportError, import_associations, read_rows


class Command(BaseCommand):
    help = "Import the CIQ of one federation from a CSV copy of the Confédération's directory."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", type=Path, help="CSV file (UTF-8)")
        parser.add_argument(
            "--federation",
            type=int,
            required=True,
            help="Federation to import, e.g. 7 for the CIQ of the 7th arrondissement",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would change, change nothing"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        path: Path = options["path"]
        try:
            with path.open(newline="", encoding="utf-8-sig") as file:
                rows = read_rows(file)
            report = import_associations(rows, options["federation"], options["dry_run"])
        except OSError as error:
            raise CommandError(f"Cannot read {path}: {error}") from error
        except AssociationImportError as error:
            raise CommandError(str(error)) from error

        prefix = "[dry run] " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}{len(report.created)} created, {len(report.updated)} updated, "
                f"{report.skipped} rows of other federations skipped."
            )
        )
        if report.invalid:
            self.stdout.write(self.style.ERROR("Not imported:"))
            for line in report.invalid:
                self.stdout.write(f"  {line}")
        if report.unlocated:
            self.stdout.write(
                self.style.WARNING(
                    "Not located, so never suggested as the nearest (they can still be chosen):"
                )
            )
            for association in report.unlocated:
                address = association.address or "no address"
                self.stdout.write(f"  {association.code} {association.name}: {address}")
