"""Download the self-hosted basemap: a PMTiles extract of the local area.

Tiles come from the daily OpenStreetMap builds published by Protomaps. Only
the tiles inside LOCAL_AREA_TILES_BOUNDS are fetched (HTTP range requests,
a few MB), so the planet file is never downloaded.

Needs the `pmtiles` CLI (https://docs.protomaps.com/pmtiles/cli), or Docker
to run it from the protomaps/go-pmtiles image.
"""

import json
import os
import shutil
import subprocess  # nosec B404 — fixed commands, no shell
import urllib.request
from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError, CommandParser

from publications.geo import (
    LOCAL_AREA_TILES_BOUNDS,
    LOCAL_AREA_TILES_MAX_ZOOM,
    LOCAL_AREA_TILES_PATH,
)

BUILDS_URL = "https://build-metadata.protomaps.dev/builds.json"
BUILD_URL = "https://build.protomaps.com/{key}"
PMTILES_IMAGE = "protomaps/go-pmtiles:v1.31.2"


def latest_build() -> str:
    """Key of the most recent planet build, e.g. "20261006.pmtiles"."""
    # The host rejects urllib's default User-Agent (403).
    request = urllib.request.Request(
        BUILDS_URL, headers={"User-Agent": "urban-platform-build-map-tiles"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 — fixed https URL
        builds = json.load(response)
    return max(build["key"] for build in builds)


def pmtiles_command(output: Path) -> list[str]:
    """The pmtiles CLI when installed, otherwise the official Docker image."""
    if binary := shutil.which("pmtiles"):
        return [binary]
    if docker := shutil.which("docker"):
        return [
            docker,
            "run",
            "--rm",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--volume",
            f"{output.parent}:{output.parent}",
            PMTILES_IMAGE,
        ]
    raise CommandError("Install the pmtiles CLI (brew install pmtiles) or Docker.")


class Command(BaseCommand):
    help = "Download the basemap tiles of the local area (PMTiles extract of OpenStreetMap)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--build",
            help='Protomaps build to extract from, e.g. "20261006.pmtiles" (default: the latest).',
        )

    def handle(self, *args: Any, **options: Any) -> None:
        output = Path(apps.get_app_config("publications").path) / "static" / LOCAL_AREA_TILES_PATH
        build = options["build"] or latest_build()
        bbox = ",".join(str(c) for c in LOCAL_AREA_TILES_BOUNDS)
        self.stdout.write(f"Extracting {bbox} up to zoom {LOCAL_AREA_TILES_MAX_ZOOM} from {build}…")

        # Write next to the target, then swap: a failed run keeps the old tiles.
        partial = output.with_suffix(".partial.pmtiles")
        command = [
            *pmtiles_command(output),
            "extract",
            BUILD_URL.format(key=build),
            str(partial),
            f"--bbox={bbox}",
            f"--maxzoom={LOCAL_AREA_TILES_MAX_ZOOM}",
        ]
        try:
            subprocess.run(command, check=True)  # nosec B603
        except subprocess.CalledProcessError as error:
            partial.unlink(missing_ok=True)
            raise CommandError(f"pmtiles extract failed ({error.returncode}).") from error
        partial.replace(output)

        size = output.stat().st_size / 1_000_000
        self.stdout.write(self.style.SUCCESS(f"Wrote {output} ({size:.1f} MB)."))
