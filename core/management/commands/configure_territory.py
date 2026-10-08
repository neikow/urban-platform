"""Set the area the website covers (see core.territories).

manage.py configure_territory 13207             # from geo.api.gouv.fr
manage.py configure_territory --file area.geojson
manage.py configure_territory 76351 --name-in "au Havre"
"""

from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from core import territories


class Command(BaseCommand):
    help = "Set the territory (outline, names, postal codes) from its INSEE code or a GeoJSON file."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("code", nargs="?", help="INSEE code of a commune or an arrondissement.")
        parser.add_argument(
            "--file", type=Path, help="A commune Feature saved from geo.api.gouv.fr, instead."
        )
        parser.add_argument("--name", help='Overrides the name, e.g. "Le Panier".')
        parser.add_argument("--name-in", help='Overrides the name in a sentence, e.g. "au Havre".')
        parser.add_argument(
            "--postal-codes", help="Overrides the local postal codes, separated by commas."
        )
        parser.add_argument(
            "--no-tiles",
            action="store_true",
            help="Do not fetch the map tiles of the new outline now (the daily check will).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if bool(options["code"]) == bool(options["file"]):
            raise CommandError("Give either an INSEE code or --file.")
        try:
            if options["file"]:
                data = territories.from_file(options["file"])
            else:
                data = territories.fetch(options["code"])
        except territories.TerritoryUnavailable as error:
            raise CommandError(str(error)) from error

        if options["name"]:
            data.name = options["name"]
        if options["name_in"]:
            data.name_in = options["name_in"]
        if options["postal_codes"] is not None:
            data.postal_codes = [c.strip() for c in options["postal_codes"].split(",") if c.strip()]

        try:
            changed = territories.apply(data)
        except ValidationError as error:
            raise CommandError(f"Invalid territory: {error}") from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Territory: {data.name} ({data.city_name}, {data.city_code}), "
                f"postal codes {', '.join(data.postal_codes) or 'none'}."
            )
        )
        if changed and not options["no_tiles"]:
            from publications.map_tiles import queue_refresh

            queue_refresh()
            self.stdout.write("Fetching the map tiles of the new outline…")
