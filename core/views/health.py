from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe for the container healthcheck: the app answers and reaches the database."""
    try:
        connection.ensure_connection()
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})
