import sys
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.conf import settings

from core.emails.services import (
    ConsoleEmailService,
    get_email_service,
    FailedToSendEmail,
)


class TestConsoleEmailService:
    def test_send_email_returns_true(self):
        service = ConsoleEmailService()
        result = service.send_email(
            to_email="test@example.com",
            to_name="Test User",
            subject="Test Subject",
            html_content="<p>Test content</p>",
        )
        assert result is True

    def test_send_email_prints_to_console(self, capsys):
        service = ConsoleEmailService()
        service.send_email(
            to_email="test@example.com",
            to_name="Test User",
            subject="Test Subject",
            html_content="<p>Test content</p>",
        )

        captured = capsys.readouterr()
        assert "EMAIL SENT" in captured.out
        assert "test@example.com" in captured.out
        assert "Test User" in captured.out
        assert "Test Subject" in captured.out
        assert "<p>Test content</p>" in captured.out

    @pytest.mark.django_db
    def test_send_verification_email(self, capsys):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="verify@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        service = ConsoleEmailService()
        result = service.send_verification_email(user, "http://example.com/verify/token/")

        assert result is True
        captured = capsys.readouterr()
        assert "verify@example.com" in captured.out
        assert "http://example.com/verify/token/" in captured.out

    @pytest.mark.django_db
    def test_send_password_reset_email(self, capsys):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="reset@example.com",
            password="testpass123",
            first_name="Reset",
            last_name="User",
        )

        service = ConsoleEmailService()
        result = service.send_password_reset_email(user, "http://example.com/reset/token/")

        assert result is True
        captured = capsys.readouterr()
        assert "reset@example.com" in captured.out
        assert "http://example.com/reset/token/" in captured.out


class TestBrevoEmailService:
    @override_settings(BREVO_API_KEY="test-api-key")
    def test_init_configures_api(self):
        mock_sdk = MagicMock()
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_api = MagicMock()

        mock_sdk.Configuration.return_value = mock_config
        mock_sdk.ApiClient.return_value = mock_client
        mock_sdk.TransactionalEmailsApi.return_value = mock_api

        with patch.dict(sys.modules, {"sib_api_v3_sdk": mock_sdk}):
            from core.emails.services import BrevoEmailService

            service = BrevoEmailService()

            mock_sdk.Configuration.assert_called_once()
            mock_sdk.ApiClient.assert_called_once_with(mock_config)
            mock_sdk.TransactionalEmailsApi.assert_called_once_with(mock_client)
            assert service.api_instance == mock_api

    @override_settings(BREVO_API_KEY="test-api-key")
    def test_send_email_success_returns_true(self):
        mock_sdk = MagicMock()
        mock_api = MagicMock()
        mock_sdk.Configuration.return_value = MagicMock()
        mock_sdk.ApiClient.return_value = MagicMock()
        mock_sdk.TransactionalEmailsApi.return_value = mock_api
        mock_sdk.SendSmtpEmail = MagicMock()

        with patch.dict(sys.modules, {"sib_api_v3_sdk": mock_sdk}):
            from core.emails.services import BrevoEmailService

            service = BrevoEmailService()

            result = service.send_email(
                to_email="test@example.com",
                to_name="Test User",
                subject="Test Subject",
                html_content="<p>Test content</p>",
            )

            assert result is True
            mock_api.send_transac_email.assert_called_once()

    @override_settings(BREVO_API_KEY="test-api-key")
    def test_send_email_failure_returns_raises_a(self):
        mock_sdk = MagicMock()
        mock_api = MagicMock()
        mock_sdk.Configuration.return_value = MagicMock()
        mock_sdk.ApiClient.return_value = MagicMock()
        mock_sdk.TransactionalEmailsApi.return_value = mock_api
        mock_sdk.SendSmtpEmail = MagicMock()
        mock_sdk.ApiException = Exception

        # Make the API call raise an exception
        mock_api.send_transac_email.side_effect = FailedToSendEmail("API Error")

        with patch.dict(sys.modules, {"sib_api_v3_sdk": mock_sdk}):
            from core.emails.services import BrevoEmailService

            service = BrevoEmailService()

            with pytest.raises(FailedToSendEmail) as exc_info:
                service.send_email(
                    to_email="test@example.com",
                    to_name="Test User",
                    subject="Test Subject",
                    html_content="<p>Test content</p>",
                )

            assert "API Error" in str(exc_info.value)


class TestGetEmailService:
    @override_settings(EMAIL_SERVICE_BACKEND="console")
    def test_get_email_service_console(self):
        service = get_email_service()
        assert isinstance(service, ConsoleEmailService)

    def test_get_email_service_brevo(self):
        mock_sdk = MagicMock()
        mock_sdk.Configuration.return_value = MagicMock()
        mock_sdk.ApiClient.return_value = MagicMock()
        mock_sdk.TransactionalEmailsApi.return_value = MagicMock()

        with patch.dict(sys.modules, {"sib_api_v3_sdk": mock_sdk}):
            with override_settings(EMAIL_SERVICE_BACKEND="brevo", BREVO_API_KEY="test-key"):
                from core.emails.services import BrevoEmailService

                service = get_email_service()
                assert isinstance(service, BrevoEmailService)

    @override_settings(EMAIL_SERVICE_BACKEND=None)
    def test_get_email_service_default_is_console(self):
        service = get_email_service()
        assert isinstance(service, ConsoleEmailService)
