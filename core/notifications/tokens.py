"""Signed tokens for one-click unsubscribe links (no login needed, no expiry)."""

from django.core import signing

from core.notifications import NotificationKind

SALT = "core.notifications.unsubscribe"


def make_unsubscribe_token(user_uuid: str, kind: NotificationKind) -> str:
    return signing.dumps({"u": str(user_uuid), "k": kind.value}, salt=SALT, compress=True)


def read_unsubscribe_token(token: str) -> tuple[str, NotificationKind] | None:
    try:
        data = signing.loads(token, salt=SALT)
        return data["u"], NotificationKind(data["k"])
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        return None
