"""runserver, with HTTP range requests on the map tiles.

The basemap is a single PMTiles archive read with range requests, which the
staticfiles handler does not support (it always answers 200 with the whole
file). In production nginx serves it. Overrides the staticfiles runserver:
this app comes first in INSTALLED_APPS.
"""

import re
from typing import Any

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.management.commands.runserver import Command as StaticfilesRunserver
from django.core.handlers.wsgi import WSGIHandler
from django.http import FileResponse, Http404, HttpRequest, HttpResponse

RANGE = re.compile(r"bytes=(\d+)-(\d*)")


def serve_range(request: HttpRequest, path: str) -> HttpResponse | None:
    """206 for a single "bytes=start-[end]" range, None when there is no range."""
    match = RANGE.fullmatch(request.headers.get("Range", ""))
    if not match:
        return None
    absolute = finders.find(path)
    if not isinstance(absolute, str):
        raise Http404(path)

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
        if path.endswith(".pmtiles") and (response := serve_range(request, path)):
            return response
        return super().serve(request)


class Command(StaticfilesRunserver):
    def get_handler(self, *args: Any, **options: Any) -> WSGIHandler:
        handler = super().get_handler(*args, **options)
        if isinstance(handler, StaticFilesHandler):
            return RangeStaticFilesHandler(handler.application)
        return handler
