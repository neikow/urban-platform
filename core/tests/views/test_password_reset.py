from unittest.mock import patch
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.emails.tokens import generate_password_reset_token

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="reset_view@example.com",
        password="oldpassword123",
        first_name="Reset",
        last_name="View",
    )


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestPasswordResetRequestView:
    def test_renders_request_form(self, client):
        response = client.get(reverse("password_reset_request"))

        assert response.status_code == 200
        assert "email" in response.content.decode().lower()

    @patch("core.views.password_reset.send_password_reset_email")
    def test_valid_email_sends_reset_email(self, mock_task, client, user):
        response = client.post(
            reverse("password_reset_request"),
            {"email": user.email},
        )

        assert response.status_code == 302
        assert response.url == reverse("password_reset_sent")
        mock_task.delay.assert_called_once_with(user.pk)

    @patch("core.views.password_reset.send_password_reset_email")
    def test_nonexistent_email_still_redirects(self, mock_task, client, db):
        response = client.post(
            reverse("password_reset_request"),
            {"email": "nonexistent@example.com"},
        )

        assert response.status_code == 302
        assert response.url == reverse("password_reset_sent")
        mock_task.delay.assert_not_called()

    def test_invalid_email_shows_error(self, client):
        response = client.post(
            reverse("password_reset_request"),
            {"email": "not-an-email"},
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestPasswordResetSentView:
    def test_renders_sent_page(self, client):
        response = client.get(reverse("password_reset_sent"))

        assert response.status_code == 200
        assert "mail" in response.content.decode().lower()


@pytest.mark.django_db
class TestPasswordResetConfirmView:
    def test_valid_token_renders_form(self, client, user):
        token = generate_password_reset_token(user.uuid)

        response = client.get(reverse("password_reset_confirm", kwargs={"token": token}))

        assert response.status_code == 200
        assert "password" in response.content.decode().lower()

    def test_invalid_token_redirects_to_error(self, client, db):
        response = client.get(reverse("password_reset_confirm", kwargs={"token": "invalid"}))

        assert response.status_code == 302
        assert response.url == reverse("password_reset_error")

    def test_valid_submission_changes_password(self, client, user):
        token = generate_password_reset_token(user.uuid)
        old_password_hash = user.password

        response = client.post(
            reverse("password_reset_confirm", kwargs={"token": token}),
            {
                "password": "NewPassword123",
                "confirm_password": "NewPassword123",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("password_reset_complete")

        user.refresh_from_db()
        assert user.password != old_password_hash
        assert user.check_password("NewPassword123")

    def test_mismatched_passwords_shows_error(self, client, user):
        token = generate_password_reset_token(user.uuid)

        response = client.post(
            reverse("password_reset_confirm", kwargs={"token": token}),
            {
                "password": "NewPassword123",
                "confirm_password": "DifferentPassword123",
            },
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("oldpassword123")

    def test_weak_password_shows_error(self, client, user):
        token = generate_password_reset_token(user.uuid)

        response = client.post(
            reverse("password_reset_confirm", kwargs={"token": token}),
            {
                "password": "weak",
                "confirm_password": "weak",
            },
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("oldpassword123")


@pytest.mark.django_db
class TestPasswordResetErrorView:
    def test_renders_error_page(self, client):
        response = client.get(reverse("password_reset_error"))

        assert response.status_code == 200
        assert (
            "expiré" in response.content.decode().lower()
            or "invalide" in response.content.decode().lower()
        )


@pytest.mark.django_db
class TestPasswordResetCompleteView:
    def test_renders_complete_page(self, client):
        response = client.get(reverse("password_reset_complete"))

        assert response.status_code == 200
        assert (
            "modifié" in response.content.decode().lower()
            or "succès" in response.content.decode().lower()
        )
