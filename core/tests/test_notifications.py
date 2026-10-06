from unittest import mock

import pytest
from django.urls import reverse

from core.models import EmailEvent, EmailEventStatus, NotificationDispatch, User
from core.notifications import NotificationKind
from core.notifications.recipients import opted_in
from core.notifications.tasks import send_notification_email
from core.notifications.tokens import make_unsubscribe_token, read_unsubscribe_token

TEMPLATE = "emails/notifications/base.html"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="notified@example.com",
        password="x",
        first_name="Nora",
        last_name="T",
        is_verified=True,
        notify_poll_results=True,
    )


class TestTokens:
    def test_round_trip(self):
        token = make_unsubscribe_token("abc", NotificationKind.EVENT_REMINDER)

        assert read_unsubscribe_token(token) == ("abc", NotificationKind.EVENT_REMINDER)

    def test_tampered_token_is_rejected(self):
        token = make_unsubscribe_token("abc", NotificationKind.EVENT_REMINDER)

        assert read_unsubscribe_token(token[:-2] + "xx") is None
        assert read_unsubscribe_token("garbage") is None


@pytest.mark.django_db
class TestUnsubscribe:
    def url(self, user, kind=NotificationKind.POLL_RESULTS):
        return reverse(
            "notification_unsubscribe", args=[make_unsubscribe_token(str(user.uuid), kind)]
        )

    def test_get_only_asks_for_confirmation(self, client, user):
        response = client.get(self.url(user))

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.notify_poll_results is True

    def test_post_unsubscribes_without_login_or_csrf(self, user):
        from django.test import Client

        response = Client(enforce_csrf_checks=True).post(self.url(user))

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.notify_poll_results is False

    def test_only_that_kind_is_turned_off(self, client, user):
        user.notify_event_reminders = True
        user.save()

        client.post(self.url(user, NotificationKind.POLL_RESULTS))

        user.refresh_from_db()
        assert (user.notify_poll_results, user.notify_event_reminders) == (False, True)

    def test_invalid_token(self, client, db):
        assert client.post("/notifications/unsubscribe/nope/").status_code == 400


@pytest.mark.django_db
class TestSendNotificationEmail:
    def send(self, user, kind=NotificationKind.POLL_RESULTS):
        with mock.patch("core.notifications.tasks.get_email_service") as service:
            service.return_value.send_email.return_value = True
            result = send_notification_email(user.pk, kind.value, "Résultats", TEMPLATE, {})
        return result, service.return_value.send_email

    def test_sends_with_one_click_unsubscribe_headers(self, user):
        sent, send_email = self.send(user)

        assert sent is True
        kwargs = send_email.call_args.kwargs
        assert kwargs["to_email"] == user.email
        assert kwargs["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
        assert "/notifications/unsubscribe/" in kwargs["headers"]["List-Unsubscribe"]
        assert "Nora" in kwargs["html_content"]
        event = EmailEvent.objects.get(user=user)
        assert (event.event_type, event.status) == ("POLL_RESULTS", EmailEventStatus.SENT)

    def test_skips_users_who_opted_out_since(self, user):
        sent, send_email = self.send(user, NotificationKind.EVENT_REMINDER)

        assert sent is False
        send_email.assert_not_called()

    def test_skips_inactive_users(self, user):
        user.is_active = False
        user.save()

        assert self.send(user)[0] is False


@pytest.mark.django_db
def test_opted_in_requires_verified_active_and_preference(user):
    unverified = User.objects.create_user(
        email="u@example.com", password="x", first_name="U", last_name="V", notify_poll_results=True
    )
    not_opted = User.objects.create_user(
        email="n@example.com", password="x", first_name="N", last_name="O", is_verified=True
    )

    result = opted_in(NotificationKind.POLL_RESULTS, [user.pk, unverified.pk, not_opted.pk])

    assert list(result) == [user]


@pytest.mark.django_db
def test_dispatch_is_claimed_once():
    assert NotificationDispatch.claim("poll_results", "project:1") is True
    assert NotificationDispatch.claim("poll_results", "project:1") is False
    assert NotificationDispatch.claim("poll_results", "project:2") is True


@pytest.mark.django_db
def test_profile_edit_saves_notification_preferences(client, user):
    client.force_login(user)

    client.post(
        reverse("profile_edit"),
        {
            "email": user.email,
            "first_name": "Nora",
            "last_name": "T",
            "postal_code": "13007",
            "notify_event_reminders": "on",
            "notify_project_updates": "on",
        },
    )

    user.refresh_from_db()
    assert (user.notify_poll_results, user.notify_project_updates, user.notify_event_reminders) == (
        False,
        True,
        True,
    )
