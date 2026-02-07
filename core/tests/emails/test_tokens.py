import time
import uuid
from django.test import override_settings

from core.emails.tokens import (
    generate_verification_token,
    verify_verification_token,
    generate_password_reset_token,
    verify_password_reset_token,
)


class TestVerificationTokens:
    def test_generate_verification_token_returns_string(self):
        user_uuid = uuid.uuid4()
        token = generate_verification_token(user_uuid)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_verification_token_returns_user_uuid(self):
        user_uuid = uuid.uuid4()
        token = generate_verification_token(user_uuid)
        result = verify_verification_token(token)
        assert result == user_uuid

    def test_verify_verification_token_invalid_returns_none(self):
        result = verify_verification_token("invalid-token")
        assert result is None

    def test_verify_verification_token_tampered_returns_none(self):
        user_uuid = uuid.uuid4()
        token = generate_verification_token(user_uuid)
        tampered_token = token[:-5] + "xxxxx"
        result = verify_verification_token(tampered_token)
        assert result is None

    @override_settings(EMAIL_VERIFICATION_TOKEN_EXPIRY=1)
    def test_verify_verification_token_expired_returns_none(self):
        user_uuid = uuid.uuid4()
        token = generate_verification_token(user_uuid)
        time.sleep(2)
        result = verify_verification_token(token)
        assert result is None

    def test_different_user_uuids_generate_different_tokens(self):
        uuid1 = uuid.uuid4()
        uuid2 = uuid.uuid4()
        token1 = generate_verification_token(uuid1)
        token2 = generate_verification_token(uuid2)
        assert token1 != token2


class TestPasswordResetTokens:
    def test_generate_password_reset_token_returns_string(self):
        user_uuid = uuid.uuid4()
        token = generate_password_reset_token(user_uuid)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_password_reset_token_returns_user_uuid(self):
        user_uuid = uuid.uuid4()
        token = generate_password_reset_token(user_uuid)
        result = verify_password_reset_token(token)
        assert result == user_uuid

    def test_verify_password_reset_token_invalid_returns_none(self):
        result = verify_password_reset_token("invalid-token")
        assert result is None

    def test_verify_password_reset_token_tampered_returns_none(self):
        user_uuid = uuid.uuid4()
        token = generate_password_reset_token(user_uuid)
        tampered_token = token[:-5] + "xxxxx"
        result = verify_password_reset_token(tampered_token)
        assert result is None

    @override_settings(PASSWORD_RESET_TOKEN_EXPIRY=1)
    def test_verify_password_reset_token_expired_returns_none(self):
        user_uuid = uuid.uuid4()
        token = generate_password_reset_token(user_uuid)
        time.sleep(2)
        result = verify_password_reset_token(token)
        assert result is None


class TestTokenSeparation:
    def test_verification_token_not_valid_for_password_reset(self):
        user_uuid = uuid.uuid4()
        token = generate_verification_token(user_uuid)
        result = verify_password_reset_token(token)
        assert result is None

    def test_password_reset_token_not_valid_for_verification(self):
        user_uuid = uuid.uuid4()
        token = generate_password_reset_token(user_uuid)
        result = verify_verification_token(token)
        assert result is None
