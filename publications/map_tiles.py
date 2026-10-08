"""The self-hosted basemap: a PMTiles extract of the local area, and its updates.

Tiles come from the daily OpenStreetMap builds published by Protomaps. Only
the tiles inside LOCAL_AREA_TILES_BOUNDS are fetched (HTTP range requests,
a few MB), so the planet file is never downloaded. Extracting needs the
`pmtiles` CLI (https://docs.protomaps.com/pmtiles/cli), or Docker to run it
from the protomaps/go-pmtiles image.

Two copies exist:
- the one in the static files, fetched when the Docker image is built
  (`manage.py build_map_tiles`): the fallback, always there;
- newer ones, fetched by the `refresh_map_tiles` task at the interval set in
  the admin (MapSettings), into the media files, which nginx serves and the
  Celery worker can write. Each extract gets its own name, so pages cached with
  the previous URL keep working: the previous file is kept as well.
"""

import json
import logging
import os
import shutil
import subprocess  # nosec B404 — fixed commands, no shell
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.templatetags.static import static
from django.utils import timezone

from publications.geo import (
    LOCAL_AREA_TILES_BOUNDS,
    LOCAL_AREA_TILES_MAX_ZOOM,
    LOCAL_AREA_TILES_PATH,
)

if TYPE_CHECKING:
    from publications.models import MapSettings

logger = logging.getLogger(__name__)

BUILDS_URL = "https://build-metadata.protomaps.dev/builds.json"
BUILD_URL = "https://build.protomaps.com/{key}"
PMTILES_IMAGE = "protomaps/go-pmtiles:v1.31.2"
# Updated extracts, relative to MEDIA_ROOT / MEDIA_URL.
MEDIA_DIRECTORY = "map-tiles"
# An extract takes a minute or two; never run two at once.
LOCK_KEY = "map-tiles:refresh"
LOCK_SECONDS = 30 * 60
# Set when an update is asked from the admin, until the task picks it up.
QUEUED_KEY = "map-tiles:queued"


class TilesError(Exception):
    """The tiles could not be fetched or extracted."""


def static_tiles_path() -> Path:
    """The tiles shipped with the static files (the fallback)."""
    return Path(apps.get_app_config("publications").path) / "static" / LOCAL_AREA_TILES_PATH


def latest_build() -> str:
    """Key of the most recent planet build, e.g. "20261006.pmtiles"."""
    # The host rejects urllib's default User-Agent (403).
    request = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "urban-platform-map-tiles"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 — fixed https URL
            builds = json.load(response)
        return str(max(build["key"] for build in builds))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise TilesError(f"Could not list the Protomaps builds: {error}") from error


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
    raise TilesError("Install the pmtiles CLI (brew install pmtiles) or Docker.")


def extract(build: str, output: Path) -> None:
    """Extract the local area from a planet build into ``output``.

    Writes next to the target, then swaps: a failed run keeps the old file.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(".partial.pmtiles")
    command = [
        *pmtiles_command(output),
        "extract",
        BUILD_URL.format(key=build),
        str(partial),
        f"--bbox={','.join(str(c) for c in LOCAL_AREA_TILES_BOUNDS)}",
        f"--maxzoom={LOCAL_AREA_TILES_MAX_ZOOM}",
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)  # nosec B603
    except subprocess.CalledProcessError as error:
        partial.unlink(missing_ok=True)
        detail = (error.stderr or "").strip().splitlines()[-1:] or [f"exit {error.returncode}"]
        raise TilesError(f"pmtiles extract failed: {detail[0]}") from error
    partial.replace(output)


def tiles_url() -> str:
    """URL of the newest tiles: the last update, or the ones shipped with the static files."""
    from publications.models import MapSettings

    name = MapSettings.load().tiles_file
    if name and (Path(settings.MEDIA_ROOT) / name).is_file():
        return f"{settings.MEDIA_URL}{name}"
    return static(LOCAL_AREA_TILES_PATH)


def last_checked(map_settings: "MapSettings") -> datetime | None:
    """When the tiles were last checked: never by the task means when the image was built."""
    if map_settings.tiles_checked_at:
        return map_settings.tiles_checked_at
    shipped = static_tiles_path()
    if shipped.is_file():
        return datetime.fromtimestamp(shipped.stat().st_mtime, tz=timezone.get_current_timezone())
    return None


def is_due(map_settings: "MapSettings", now: datetime) -> bool:
    if not map_settings.tiles_auto_update:
        return False
    checked = last_checked(map_settings)
    return checked is None or now - checked >= timedelta(
        days=map_settings.tiles_update_interval_days
    )


def _prune(keep: set[str]) -> None:
    """Delete older extracts, keeping ``keep`` (paths relative to MEDIA_ROOT)."""
    directory = Path(settings.MEDIA_ROOT) / MEDIA_DIRECTORY
    for path in directory.glob("*.pmtiles"):
        if path.relative_to(settings.MEDIA_ROOT).as_posix() not in keep:
            path.unlink(missing_ok=True)


def is_refreshing() -> bool:
    """Whether an update is queued or running (shown in the admin)."""
    return bool(cache.get(QUEUED_KEY) or cache.get(LOCK_KEY))


def queue_refresh() -> bool:
    """Ask the worker for an update now, whatever the interval. False if one is under way."""
    from publications.tasks import refresh_map_tiles

    if is_refreshing() or not cache.add(QUEUED_KEY, True, LOCK_SECONDS):
        return False
    refresh_map_tiles.delay(force=True)  # type: ignore[attr-defined]  # Celery task
    return True


def refresh_tiles(force: bool = False) -> str | None:
    """Fetch newer tiles when due (or ``force``). Returns the new file, or None if unchanged.

    The outcome (version, date, error) is recorded on MapSettings for the admin.
    """
    from core.cache import clear_content_cache
    from publications.models import MapSettings

    map_settings = MapSettings.load()
    now = timezone.now()
    if not force and not is_due(map_settings, now):
        return None
    if not cache.add(LOCK_KEY, True, LOCK_SECONDS):
        logger.info("Map tiles refresh already running.")
        return None
    cache.delete(QUEUED_KEY)

    status = MapSettings.objects.filter(pk=map_settings.pk)
    try:
        build = latest_build()
        current = map_settings.tiles_file
        if not force and build == map_settings.tiles_build and current:
            if (Path(settings.MEDIA_ROOT) / current).is_file():
                status.update(tiles_checked_at=now, tiles_error="")
                return None

        name = f"{MEDIA_DIRECTORY}/local-area-{Path(build).stem}.pmtiles"
        extract(build, Path(settings.MEDIA_ROOT) / name)
    except TilesError as error:
        logger.warning("Map tiles refresh failed: %s", error)
        status.update(tiles_checked_at=now, tiles_error=str(error)[:1000])
        return None
    finally:
        cache.delete(LOCK_KEY)

    status.update(
        tiles_build=build,
        tiles_file=name,
        tiles_updated_at=now,
        tiles_checked_at=now,
        tiles_error="",
    )
    _prune(keep={name, current})
    # Cached page fragments embed the tiles URL.
    clear_content_cache()
    logger.info("Map tiles updated to %s.", build)
    return name
