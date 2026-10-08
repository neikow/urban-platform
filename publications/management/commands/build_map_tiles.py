"""Download the basemap tiles of the territory into the static files (development).

Online, the `refresh_map_tiles` task fetches them into the media files (see
publications.map_tiles); `--refresh` runs it now, whatever the interval.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from publications.geo import LOCAL_AREA_TILES_MAX_ZOOM
from publications.map_tiles import (
    TilesError,
    current_bounds,
    extract,
    latest_build,
    refresh_tiles,
    static_tiles_path,
)


class Command(BaseCommand):
    help = "Download the basemap tiles of the local area (PMTiles extract of OpenStreetMap)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--build",
            help='Protomaps build to extract from, e.g. "20261006.pmtiles" (default: the latest).',
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Update the tiles served from the media files now, as the scheduled task does.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["refresh"]:
            name = refresh_tiles(force=True)
            if name is None:
                raise CommandError("The refresh failed: see the error under Settings › Map.")
            self.stdout.write(self.style.SUCCESS(f"Updated the map tiles: {name}."))
            return

        output = static_tiles_path()
        try:
            build = options["build"] or latest_build()
            extent = current_bounds()
            bbox = ",".join(str(c) for c in extent)
            self.stdout.write(
                f"Extracting {bbox} up to zoom {LOCAL_AREA_TILES_MAX_ZOOM} from {build}…"
            )
            extract(build, output, extent)
        except TilesError as error:
            raise CommandError(str(error)) from error

        size = output.stat().st_size / 1_000_000
        self.stdout.write(self.style.SUCCESS(f"Wrote {output} ({size:.1f} MB)."))
