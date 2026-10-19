"""Import neighborhood associations (CIQ) from a CSV copy of the Confédération's directory.

The directory numbers each CIQ: the hundreds are its federation, which is its
arrondissement in Marseille (701 to 716 for the 7th), and NN00 is the
federation itself. Only the CIQ of the federation given with --federation are
imported. The file is not kept in the repository: it holds personal contacts.

Columns (header row required): code, name, address, contact_email,
contact_phone, website. Only code and name are required; an address without a
postcode is looked up in Marseille.

Running it again updates the associations by code (or by name for those
created by hand, which then get their code). Residents are matched again once,
at the end.
"""

import csv
import re
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from core.associations import paused_reassignment
from core.models import NeighborhoodAssociation

FIELDS = ("name", "address", "contact_email", "contact_phone", "website")


def federation_of(code: str) -> int | None:
    """701 → 7, 1012 → 10; None for a federation itself (700) or a code that is not a number."""
    if not code.isdigit() or int(code) % 100 == 0:
        return None
    return int(code) // 100


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
        rows = self.read(options["path"])
        wanted = [row for row in rows if federation_of(row["code"]) == options["federation"]]
        if not wanted:
            raise CommandError(f"No CIQ of federation {options['federation']} in the file.")

        created = updated = 0
        unlocated: list[str] = []
        invalid: list[str] = []
        with transaction.atomic(), paused_reassignment():
            for row in wanted:
                try:
                    association, is_new = self.upsert(row)
                except ValidationError as error:
                    invalid.append(f"{row['code']} {row['name']}: {'; '.join(error.messages)}")
                    continue
                created += is_new
                updated += not is_new
                if association.address and not association.address_location:
                    unlocated.append(
                        f"{association.code} {association.name}: {association.address}"
                    )
                elif not association.address:
                    unlocated.append(f"{association.code} {association.name}: no address")
            if options["dry_run"]:
                transaction.set_rollback(True)

        prefix = "[dry run] " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}{created} created, {updated} updated, "
                f"{len(rows) - len(wanted)} rows of other federations skipped."
            )
        )
        if invalid:
            self.stdout.write(self.style.ERROR("Not imported:"))
            for line in invalid:
                self.stdout.write(f"  {line}")
        if unlocated:
            self.stdout.write(
                self.style.WARNING(
                    "Not located, so never suggested as the nearest (they can still be chosen):"
                )
            )
            for line in unlocated:
                self.stdout.write(f"  {line}")

    def read(self, path: Path) -> list[dict[str, str]]:
        try:
            with path.open(newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                missing = {"code", "name"} - set(reader.fieldnames or [])
                if missing:
                    raise CommandError(f"Missing columns: {', '.join(sorted(missing))}")
                return [
                    {key: (value or "").strip() for key, value in row.items() if key}
                    for row in reader
                ]
        except OSError as error:
            raise CommandError(f"Cannot read {path}: {error}") from error

    def upsert(self, row: dict[str, str]) -> tuple[NeighborhoodAssociation, bool]:
        association = (
            NeighborhoodAssociation.objects.filter(code=row["code"]).first()
            or NeighborhoodAssociation.objects.filter(code="", name__iexact=row["name"]).first()
        )
        is_new = association is None
        if association is None:
            association = NeighborhoodAssociation()
        association.code = row["code"]
        for field in FIELDS:
            if field in row:
                setattr(association, field, row[field])
        if association.address and not re.search(r"\b\d{5}\b|marseille", association.address, re.I):
            association.address = f"{association.address}, Marseille"
        association.full_clean()  # locates the address
        association.save()
        return association, is_new
