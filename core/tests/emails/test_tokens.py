import time
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from core.emails.tokens import (
    generate_verification_token,
    verify_verification_token,
    generate_password_reset_token,
    verify_password_reset_token,
)

User = get_user_model()


@pytest.fixture
def reset_user(db):
    return User.objects.create_user(
        email="reset@example.com",
        password="InitialPass123",
        first_name="Reset",
        last_name="User",
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


@pytest.mark.django_db
class TestPasswordResetTokens:
    def test_generate_password_reset_token_returns_string(self, reset_user):
        token = generate_password_reset_token(reset_user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_password_reset_token_returns_user_uuid(self, reset_user):
        token = generate_password_reset_token(reset_user)
        result = verify_password_reset_token(token)
        assert result == reset_user.uuid

    def test_verify_password_reset_token_invalid_returns_none(self):
        result = verify_password_reset_token("invalid-token")
        assert result is None

    def test_verify_password_reset_token_tampered_returns_none(self, reset_user):
        token = generate_password_reset_token(reset_user)
        tampered_token = token[:-5] + "xxxxx"
        result = verify_password_reset_token(tampered_token)
        assert result is None

    @override_settings(PASSWORD_RESET_TOKEN_EXPIRY=1)
    def test_verify_password_reset_token_expired_returns_none(self, reset_user):
        token = generate_password_reset_token(reset_user)
        time.sleep(2)
        result = verify_password_reset_token(token)
        assert result is None

    def test_token_for_unknown_user_returns_none(self, reset_user):
        token = generate_password_reset_token(reset_user)
        reset_user.delete()
        assert verify_password_reset_token(token) is None

    def test_token_is_single_use_after_password_change(self, reset_user):
        token = generate_password_reset_token(reset_user)
        assert verify_password_reset_token(token) == reset_user.uuid

        # Completing the reset (or any password change) must invalidate the token.
        reset_user.set_password("BrandNewPass456")
        reset_user.save(update_fields=["password"])

        assert verify_password_reset_token(token) is None


@pytest.mark.django_db
class TestTokenSeparation:
    def test_verification_token_not_valid_for_password_reset(self, reset_user):
        token = generate_verification_token(reset_user.uuid)
        result = verify_password_reset_token(token)
        assert result is None

    def test_password_reset_token_not_valid_for_verification(self, reset_user):
        token = generate_password_reset_token(reset_user)
        result = verify_verification_token(token)
        assert result is None
