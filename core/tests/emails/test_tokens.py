import time
from unittest.mock import patch

import pytest
from django.test import override_settings

from core.emails.tokens import (
    generate_verification_token,
    verify_verification_token,
    generate_password_reset_token,
    verify_password_reset_token,
)


class TestVerificationTokens:
    def test_generate_verification_token_returns_string(self):
        token = generate_verification_token(123)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_verification_token_returns_user_id(self):
        user_id = 456
        token = generate_verification_token(user_id)
        result = verify_verification_token(token)
        assert result == user_id

    def test_verify_verification_token_invalid_returns_none(self):
        result = verify_verification_token("invalid-token")
        assert result is None

    def test_verify_verification_token_tampered_returns_none(self):
        token = generate_verification_token(123)
        tampered_token = token[:-5] + "xxxxx"
        result = verify_verification_token(tampered_token)
        assert result is None

    @override_settings(EMAIL_VERIFICATION_TOKEN_EXPIRY=1)
    def test_verify_verification_token_expired_returns_none(self):
        token = generate_verification_token(123)
        time.sleep(2)
        result = verify_verification_token(token)
        assert result is None

    def test_different_user_ids_generate_different_tokens(self):
        token1 = generate_verification_token(1)
        token2 = generate_verification_token(2)
        assert token1 != token2


class TestPasswordResetTokens:
    def test_generate_password_reset_token_returns_string(self):
        token = generate_password_reset_token(123)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_password_reset_token_returns_user_id(self):
        user_id = 789
        token = generate_password_reset_token(user_id)
        result = verify_password_reset_token(token)
        assert result == user_id

    def test_verify_password_reset_token_invalid_returns_none(self):
        result = verify_password_reset_token("invalid-token")
        assert result is None

    def test_verify_password_reset_token_tampered_returns_none(self):
        token = generate_password_reset_token(123)
        tampered_token = token[:-5] + "xxxxx"
        result = verify_password_reset_token(tampered_token)
        assert result is None

    @override_settings(PASSWORD_RESET_TOKEN_EXPIRY=1)
    def test_verify_password_reset_token_expired_returns_none(self):
        token = generate_password_reset_token(123)
        time.sleep(2)
        result = verify_password_reset_token(token)
        assert result is None


class TestTokenSeparation:
    def test_verification_token_not_valid_for_password_reset(self):
        token = generate_verification_token(123)
        result = verify_password_reset_token(token)
        assert result is None

    def test_password_reset_token_not_valid_for_verification(self):
        token = generate_password_reset_token(123)
        result = verify_verification_token(token)
        assert result is None
