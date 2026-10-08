"""runserver, with HTTP range requests on the map tiles.

The basemap is a single PMTiles archive read with range requests, which the
staticfiles handler and the media view do not support (they always answer 200
with the whole file). In production nginx serves it. Overrides the staticfiles
runserver: this app comes first in INSTALLED_APPS. Media tiles go through
``serve_media_tiles`` (urls.py, DEBUG only).
"""

import re
from pathlib import Path
from typing import Any

from django.conf import settings

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.management.commands.runserver import Command as StaticfilesRunserver
from django.core.handlers.wsgi import WSGIHandler
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.views.static import serve

RANGE = re.compile(r"bytes=(\d+)-(\d*)")


def serve_range(request: HttpRequest, absolute: str | Path) -> HttpResponse | None:
    """206 for a single "bytes=start-[end]" range, None when there is no range."""
    match = RANGE.fullmatch(request.headers.get("Range", ""))
    if not match:
        return None
    with open(absolute, "rb") as file:
        size = file.seek(0, 2)
        start = int(match[1])
        end = min(int(match[2]) if match[2] else size - 1, size - 1)
        if start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        file.seek(start)
        response = HttpResponse(
            file.read(end - start + 1), status=206, content_type="application/octet-stream"
        )
    response["Content-Range"] = f"bytes {start}-{end}/{size}"
    response["Accept-Ranges"] = "bytes"
    return response


class RangeStaticFilesHandler(StaticFilesHandler):
    def serve(self, request: HttpRequest) -> HttpResponse | FileResponse:
        path = self.file_path(request.path)
        if path.endswith(".pmtiles") and "Range" in request.headers:
            absolute = finders.find(path)
            if not isinstance(absolute, str):
                raise Http404(path)
            if response := serve_range(request, absolute):
                return response
        return super().serve(request)


def serve_media_tiles(request: HttpRequest, path: str) -> HttpResponse | FileResponse:
    """Media files view for .pmtiles archives, with range requests (development only)."""
    root = Path(settings.MEDIA_ROOT).resolve()
    absolute = (root / path).resolve()
    if not absolute.is_relative_to(root) or not absolute.is_file():
        raise Http404(path)
    return serve_range(request, absolute) or serve(request, path, document_root=str(root))


class Command(StaticfilesRunserver):
    def get_handler(self, *args: Any, **options: Any) -> WSGIHandler:
        handler = super().get_handler(*args, **options)
        if isinstance(handler, StaticFilesHandler):
            return RangeStaticFilesHandler(handler.application)
        return handler
