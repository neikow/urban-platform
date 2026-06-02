from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils.crypto import constant_time_compare, salted_hmac

if TYPE_CHECKING:
    from core.models import User

VERIFICATION_SALT = "email-verification"
PASSWORD_RESET_SALT = "password-reset"  # nosec B105
_PASSWORD_MARKER_SALT = "core.emails.tokens.password-reset-marker"  # nosec B105


def generate_verification_token(user_uuid: UUID) -> str:
    signer = TimestampSigner(salt=VERIFICATION_SALT)
    return signer.sign(str(user_uuid))


def verify_verification_token(token: str) -> UUID | None:
    signer = TimestampSigner(salt=VERIFICATION_SALT)
    max_age = getattr(settings, "EMAIL_VERIFICATION_TOKEN_EXPIRY", 86400)
    try:
        user_uuid_str = signer.unsign(token, max_age=max_age)
        return UUID(user_uuid_str)
    except (BadSignature, SignatureExpired, ValueError):
        return None


def _password_marker(user: "User") -> str:
    """A short, non-reversible fingerprint of the user's current password hash.

    Embedding it in the reset token makes the token effectively single-use:
    once the password changes — including by completing the reset itself — the
    marker no longer matches and the old token is rejected. This mirrors what
    Django's built-in ``PasswordResetTokenGenerator`` achieves.
    """
    return salted_hmac(_PASSWORD_MARKER_SALT, user.password).hexdigest()[:32]


def generate_password_reset_token(user: "User") -> str:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    return signer.sign(f"{user.uuid}:{_password_marker(user)}")


def verify_password_reset_token(token: str) -> UUID | None:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    max_age = getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRY", 3600)
    try:
        value = signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

    user_uuid_str, separator, marker = value.partition(":")
    if not separator or not marker:
        return None
    try:
        user_uuid = UUID(user_uuid_str)
    except ValueError:
        return None

    user_model = get_user_model()
    user = user_model.objects.filter(uuid=user_uuid).first()
    if user is None:
        return None
    # Reject the token if the password has changed since it was issued.
    if not constant_time_compare(marker, _password_marker(user)):
        return None
    return user_uuid
