from django.conf import settings
from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe: the app answers and reaches the database.

    Also says which release runs, for the deployment agent to confirm an update.
    """
    try:
        connection.ensure_connection()
    except DatabaseError:
        return JsonResponse(
            {"status": "error", "database": "unreachable", "version": settings.APP_VERSION},
            status=503,
        )
    return JsonResponse({"status": "ok", "version": settings.APP_VERSION})
