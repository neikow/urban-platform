import os

import sentry_sdk
from django.core.exceptions import DisallowedHost
from sentry_sdk.types import Event, Hint


def _before_send(event: Event, hint: Hint) -> Event | None:
    """Drop noisy, non-actionable events before sending to Sentry."""
    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type, _exc_value, _tb = exc_info
        # Invalid HTTP_HOST header probes hitting the server by raw IP.
        if issubclass(exc_type, DisallowedHost):
            return None

    logentry = event.get("logentry") or {}
    raw = logentry.get("formatted") or logentry.get("message") or event.get("message")
    message = raw if isinstance(raw, str) else ""
    # Celery/kombu retry spam when Redis broker is temporarily unreachable.
    if "Cannot connect to redis" in message or "Connection refused" in message:
        return None

    return event


def setup_sentry(dsn: str, environment: str) -> None:
    if environment not in ["production", "staging"]:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=os.environ.get("SENTRY_RELEASE"),
        send_default_pii=True,
        traces_sample_rate=1.0,
        before_send=_before_send,
    )
