"""Import neighborhood associations (CIQ) from a CSV copy of the Confédération's directory.

The directory numbers each CIQ: the hundreds are its federation, which is its
arrondissement in Marseille (701 to 716 for the 7th), and NN00 is the
federation itself. Only the CIQ of the chosen federation are imported. The file
is not kept: it holds personal contacts.

Columns (header row required): code, name, address, contact_email,
contact_phone, website. Only code and name are required; an address without a
postcode is looked up in Marseille.

Running it again updates the associations by code (or by name for those
created by hand, which then get their code). Residents are matched again once,
at the end.

Used by the import_associations command and by Settings › Neighborhood
associations › Import (core.views.association_import).
"""

import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from core.associations import paused_reassignment
from core.models import NeighborhoodAssociation

FIELDS = ("name", "address", "contact_email", "contact_phone", "website")
REQUIRED_COLUMNS = {"code", "name"}


class AssociationImportError(Exception):
    """The file cannot be imported at all."""


@dataclass
class ImportReport:
    created: list[NeighborhoodAssociation] = field(default_factory=list)
    updated: list[NeighborhoodAssociation] = field(default_factory=list)
    skipped: int = 0  # rows of other federations
    invalid: list[str] = field(default_factory=list)  # "code name: reason"
    # Without an address, or with one the address service did not find.
    unlocated: list[NeighborhoodAssociation] = field(default_factory=list)


def federation_of(code: str) -> int | None:
    """701 → 7, 1012 → 10; None for a federation itself (700) or a code that is not a number."""
    if not code.isdigit() or int(code) % 100 == 0:
        return None
    return int(code) // 100


def read_rows(lines: Iterable[str]) -> list[dict[str, str]]:
    """The rows of a CSV file opened as text, values stripped."""
    try:
        reader = csv.DictReader(lines)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise AssociationImportError(
                _("Missing columns: %(columns)s") % {"columns": ", ".join(sorted(missing))}
            )
        return [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]
    except csv.Error as error:
        raise AssociationImportError(
            _("Not a valid CSV file: %(error)s") % {"error": error}
        ) from error


def import_associations(
    rows: list[dict[str, str]], federation: int, dry_run: bool = False
) -> ImportReport:
    wanted = [row for row in rows if federation_of(row["code"]) == federation]
    if not wanted:
        raise AssociationImportError(
            _("No CIQ of federation %(federation)s in the file.") % {"federation": federation}
        )

    report = ImportReport(skipped=len(rows) - len(wanted))
    with transaction.atomic(), paused_reassignment():
        for row in wanted:
            try:
                association, is_new = upsert(row)
            except ValidationError as error:
                report.invalid.append(f"{row['code']} {row['name']}: {'; '.join(error.messages)}")
                continue
            (report.created if is_new else report.updated).append(association)
            if not association.address_location:
                report.unlocated.append(association)
        if dry_run:
            transaction.set_rollback(True)
    return report


def upsert(row: dict[str, str]) -> tuple[NeighborhoodAssociation, bool]:
    association = (
        NeighborhoodAssociation.objects.filter(code=row["code"]).first()
        or NeighborhoodAssociation.objects.filter(code="", name__iexact=row["name"]).first()
    )
    is_new = association is None
    if association is None:
        association = NeighborhoodAssociation()
    association.code = row["code"]
    for name in FIELDS:
        if name in row:
            setattr(association, name, row[name])
    if association.address and not re.search(r"\b\d{5}\b|marseille", association.address, re.I):
        association.address = f"{association.address}, Marseille"
    association.full_clean()  # locates the address
    association.save()
    return association, is_new
