from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from core.emails.tasks import (
    send_verification_email,
    send_password_reset_email,
    anonymize_old_email_events,
)
from core.models import EmailEvent, EmailEventStatus, EmailEventType

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="task_test@example.com",
        password="testpass123",
        first_name="Task",
        last_name="Test",
    )


@pytest.mark.django_db
class TestSendVerificationEmail:
    @patch("core.emails.tasks.get_email_service")
    def test_creates_email_event(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = True
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        assert event is not None
        assert event.event_type == EmailEventType.VERIFICATION
        assert event.recipient_email == user.email

    @patch("core.emails.tasks.get_email_service")
    def test_marks_event_sent_on_success(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = True
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        assert event.status == EmailEventStatus.SENT
        assert event.sent_at is not None

    @patch("core.emails.tasks.get_email_service")
    def test_marks_event_failed_on_failure(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = False
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        assert event.status == EmailEventStatus.FAILED

    def test_returns_false_for_nonexistent_user(self, db):
        result = send_verification_email(99999)
        assert result is False

    @patch("core.emails.tasks.get_email_service")
    def test_generates_correct_verification_url(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = True
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        call_args = mock_service.send_verification_email.call_args
        verification_url = call_args[0][1]
        assert "/auth/verify-email/" in verification_url


@pytest.mark.django_db
class TestSendPasswordResetEmail:
    @patch("core.emails.tasks.get_email_service")
    def test_creates_email_event(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_password_reset_email.return_value = True
        mock_get_service.return_value = mock_service

        send_password_reset_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        assert event is not None
        assert event.event_type == EmailEventType.PASSWORD_RESET
        assert event.recipient_email == user.email

    @patch("core.emails.tasks.get_email_service")
    def test_marks_event_sent_on_success(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_password_reset_email.return_value = True
        mock_get_service.return_value = mock_service

        send_password_reset_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        assert event.status == EmailEventStatus.SENT
        assert event.sent_at is not None

    @patch("core.emails.tasks.get_email_service")
    def test_marks_event_failed_on_failure(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_password_reset_email.return_value = False
        mock_get_service.return_value = mock_service

        send_password_reset_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        assert event.status == EmailEventStatus.FAILED

    def test_returns_false_for_nonexistent_user(self, db):
        result = send_password_reset_email(99999)
        assert result is False

    @patch("core.emails.tasks.get_email_service")
    def test_generates_correct_reset_url(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_password_reset_email.return_value = True
        mock_get_service.return_value = mock_service

        send_password_reset_email(user.pk)

        call_args = mock_service.send_password_reset_email.call_args
        reset_url = call_args[0][1]
        assert "/auth/password-reset/" in reset_url


@pytest.mark.django_db
class TestAnonymizeOldEmailEvents:
    @patch("core.emails.tasks.get_email_service")
    def test_anonymizes_old_events(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = True
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        event.created_at = timezone.now() - timedelta(days=31)
        event.save(update_fields=["created_at"])

        count = anonymize_old_email_events()

        assert count == 1
        event.refresh_from_db()
        assert event.user is None
        assert event.recipient_email == ""

    @patch("core.emails.tasks.get_email_service")
    def test_does_not_anonymize_recent_events(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = True
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        count = anonymize_old_email_events()

        assert count == 0
        event = EmailEvent.objects.filter(user=user).first()
        assert event.user == user
        assert event.recipient_email == user.email

    @override_settings(EMAIL_EVENT_ANONYMIZE_DAYS=7)
    @patch("core.emails.tasks.get_email_service")
    def test_respects_custom_anonymize_days(self, mock_get_service, user):
        mock_service = MagicMock()
        mock_service.send_verification_email.return_value = True
        mock_get_service.return_value = mock_service

        send_verification_email(user.pk)

        event = EmailEvent.objects.filter(user=user).first()
        event.created_at = timezone.now() - timedelta(days=8)
        event.save(update_fields=["created_at"])

        count = anonymize_old_email_events()

        assert count == 1
        event.refresh_from_db()
        assert event.user is None
