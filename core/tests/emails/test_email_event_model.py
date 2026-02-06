import pytest
from django.contrib.auth import get_user_model

from core.models import EmailEvent, EmailEventStatus, EmailEventType

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="model_test@example.com",
        password="testpass123",
        first_name="Model",
        last_name="Test",
    )


@pytest.mark.django_db
class TestEmailEvent:
    def test_create_email_event(self, user):
        event = EmailEvent.objects.create(
            user=user,
            event_type=EmailEventType.VERIFICATION,
            status=EmailEventStatus.PENDING,
            recipient_email=user.email,
        )

        assert event.id is not None
        assert event.user == user
        assert event.event_type == EmailEventType.VERIFICATION
        assert event.status == EmailEventStatus.PENDING
        assert event.recipient_email == user.email
        assert event.created_at is not None

    def test_email_event_str(self, user):
        event = EmailEvent.objects.create(
            user=user,
            event_type=EmailEventType.VERIFICATION,
            status=EmailEventStatus.SENT,
            recipient_email=user.email,
        )

        str_repr = str(event)
        assert EmailEventType.VERIFICATION in str_repr
        assert EmailEventStatus.SENT in str_repr

    def test_anonymize_clears_user_and_email(self, user):
        event = EmailEvent.objects.create(
            user=user,
            event_type=EmailEventType.PASSWORD_RESET,
            status=EmailEventStatus.SENT,
            recipient_email=user.email,
        )

        event.anonymize()

        event.refresh_from_db()
        assert event.user is None
        assert event.recipient_email == ""

    def test_user_deletion_sets_null(self, user):
        event = EmailEvent.objects.create(
            user=user,
            event_type=EmailEventType.VERIFICATION,
            status=EmailEventStatus.SENT,
            recipient_email=user.email,
        )

        user.delete()

        event.refresh_from_db()
        assert event.user is None
        assert event.recipient_email == user.email

    def test_default_status_is_pending(self, user):
        event = EmailEvent.objects.create(
            user=user,
            event_type=EmailEventType.VERIFICATION,
            recipient_email=user.email,
        )

        assert event.status == EmailEventStatus.PENDING

    def test_event_type_choices(self):
        assert EmailEventType.VERIFICATION == "VERIFICATION"
        assert EmailEventType.PASSWORD_RESET == "PASSWORD_RESET"

    def test_event_status_choices(self):
        assert EmailEventStatus.PENDING == "PENDING"
        assert EmailEventStatus.SENT == "SENT"
        assert EmailEventStatus.FAILED == "FAILED"
