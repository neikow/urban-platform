from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

VERIFICATION_SALT = "email-verification"
PASSWORD_RESET_SALT = "password-reset"  # nosec - This salt is not used for security purposes, just to namespace the tokens.


def generate_verification_token(user_id: int) -> str:
    signer = TimestampSigner(salt=VERIFICATION_SALT)
    return signer.sign(str(user_id))


def verify_verification_token(token: str) -> int | None:
    signer = TimestampSigner(salt=VERIFICATION_SALT)
    max_age = getattr(settings, "EMAIL_VERIFICATION_TOKEN_EXPIRY", 86400)
    try:
        user_id = signer.unsign(token, max_age=max_age)
        return int(user_id)
    except (BadSignature, SignatureExpired, ValueError):
        return None


def generate_password_reset_token(user_id: int) -> str:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    return signer.sign(str(user_id))


def verify_password_reset_token(token: str) -> int | None:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    max_age = getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRY", 3600)
    try:
        user_id = signer.unsign(token, max_age=max_age)
        return int(user_id)
    except (BadSignature, SignatureExpired, ValueError):
        return None
