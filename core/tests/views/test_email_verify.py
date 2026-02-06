from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.emails.tokens import generate_verification_token

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="verify_view@example.com",
        password="testpass123",
        first_name="Verify",
        last_name="View",
        is_verified=False,
    )


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestEmailVerifyView:
    def test_valid_token_verifies_user(self, client, user):
        token = generate_verification_token(user.pk)

        response = client.get(reverse("email_verify", kwargs={"token": token}))

        assert response.status_code == 302
        assert response.url == reverse("email_verify_success")

        user.refresh_from_db()
        assert user.is_verified is True

    def test_invalid_token_redirects_to_error(self, client, user):
        response = client.get(reverse("email_verify", kwargs={"token": "invalid-token"}))

        assert response.status_code == 302
        assert response.url == reverse("email_verify_error")

        user.refresh_from_db()
        assert user.is_verified is False

    def test_already_verified_user_still_succeeds(self, client, user):
        user.is_verified = True
        user.save()

        token = generate_verification_token(user.pk)
        response = client.get(reverse("email_verify", kwargs={"token": token}))

        assert response.status_code == 302
        assert response.url == reverse("email_verify_success")

    def test_nonexistent_user_redirects_to_error(self, client, db):
        token = generate_verification_token(99999)
        response = client.get(reverse("email_verify", kwargs={"token": token}))

        assert response.status_code == 302
        assert response.url == reverse("email_verify_error")


@pytest.mark.django_db
class TestEmailVerifySuccessView:
    def test_renders_success_page(self, client):
        response = client.get(reverse("email_verify_success"))

        assert response.status_code == 200
        assert "confirmé" in response.content.decode().lower()


@pytest.mark.django_db
class TestEmailVerifyErrorView:
    def test_renders_error_page(self, client):
        response = client.get(reverse("email_verify_error"))

        assert response.status_code == 200
        assert (
            "expiré" in response.content.decode().lower()
            or "invalide" in response.content.decode().lower()
        )
