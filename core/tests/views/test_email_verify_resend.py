from unittest import mock

import pytest
from django.urls import reverse

from core.models import User


@pytest.fixture
def unverified_user(db):
    return User.objects.create_user(
        email="resend@example.com", password="TestPass123", first_name="A", last_name="B"
    )


@pytest.mark.django_db
class TestEmailVerifyResend:
    url = reverse("email_verify_resend")

    def test_requires_login(self, client):
        response = client.post(self.url)

        assert response.status_code == 302
        assert reverse("login") in response.url

    def test_sends_new_link(self, client, unverified_user):
        client.force_login(unverified_user)

        with mock.patch("core.views.email_verify.send_verification_email") as task:
            response = client.post(self.url)

        task.delay.assert_called_once_with(unverified_user.pk)
        assert response.status_code == 302
        assert response.url == reverse("me")

    def test_already_verified_sends_nothing(self, client, unverified_user):
        unverified_user.is_verified = True
        unverified_user.save()
        client.force_login(unverified_user)

        with mock.patch("core.views.email_verify.send_verification_email") as task:
            client.post(self.url)

        task.delay.assert_not_called()

    def test_redirects_to_safe_next(self, client, unverified_user):
        client.force_login(unverified_user)

        with mock.patch("core.views.email_verify.send_verification_email"):
            response = client.post(self.url, {"next": "/publications/some-project/"})

        assert response.url == "/publications/some-project/"

    def test_ignores_external_next(self, client, unverified_user):
        client.force_login(unverified_user)

        with mock.patch("core.views.email_verify.send_verification_email"):
            response = client.post(self.url, {"next": "https://evil.example.com/"})

        assert response.url == reverse("me")

    def test_rate_limited(self, client, unverified_user):
        client.force_login(unverified_user)

        with (
            mock.patch("core.views.email_verify.send_verification_email") as task,
            mock.patch("django_ratelimit.decorators.is_ratelimited", return_value=True),
        ):
            client.post(self.url)

        task.delay.assert_not_called()
