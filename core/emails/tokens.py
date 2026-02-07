from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from uuid import UUID

VERIFICATION_SALT = "email-verification"
PASSWORD_RESET_SALT = "password-reset"  # nosec B105


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


def generate_password_reset_token(user_uuid: UUID) -> str:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    return signer.sign(str(user_uuid))


def verify_password_reset_token(token: str) -> UUID | None:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    max_age = getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRY", 3600)
    try:
        user_uuid_str = signer.unsign(token, max_age=max_age)
        return UUID(user_uuid_str)
    except (BadSignature, SignatureExpired, ValueError):
        return None
