import json
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestLoginForm:
    def test_login_form_valid_data(self, client: Client):
        User.objects.create_user(
            email="testuser@example.com",
            password="TestPass123",
            first_name="Test",
            last_name="User",
        )

        response = client.post(
            reverse("login"),
            data={
                "email": "testuser@example.com",
                "password": "TestPass123",
            },
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True
        assert data["redirect"] == "/auth/me/"

    def test_login_form_invalid_email(self, client: Client):
        response = client.post(
            reverse("login"),
            data={
                "email": "nonexistent@example.com",
                "password": "TestPass123",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["success"] is False
        assert "errors" in data

    def test_login_form_wrong_password(self, client: Client):
        User.objects.create_user(
            email="testuser@example.com",
            password="CorrectPass123",
            first_name="Test",
            last_name="User",
        )

        response = client.post(
            reverse("login"),
            data={
                "email": "testuser@example.com",
                "password": "WrongPass123",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["success"] is False
        assert "errors" in data

    def test_login_form_missing_email(self, client: Client):
        response = client.post(
            reverse("login"),
            data={
                "password": "TestPass123",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["success"] is False
        assert "email" in data["errors"]

    def test_login_form_missing_password(self, client: Client):
        response = client.post(
            reverse("login"),
            data={
                "email": "testuser@example.com",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["success"] is False
        assert "password" in data["errors"]

    def test_login_form_invalid_email_format(self, client: Client):
        response = client.post(
            reverse("login"),
            data={
                "email": "not-an-email",
                "password": "TestPass123",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["success"] is False
        assert "email" in data["errors"]


@pytest.mark.django_db
class TestLoginView:
    def test_user_logged_in_after_successful_login(self, client: Client):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="TestPass123",
            first_name="Test",
            last_name="User",
        )

        response = client.post(
            reverse("login"),
            data={
                "email": "testuser@example.com",
                "password": "TestPass123",
            },
        )

        assert response.status_code == 200
        assert client.session["_auth_user_id"] == str(user.pk)

    def test_login_redirects_to_me_page(self, client: Client):
        User.objects.create_user(
            email="testuser@example.com",
            password="TestPass123",
            first_name="Test",
            last_name="User",
        )

        response = client.post(
            reverse("login"),
            data={
                "email": "testuser@example.com",
                "password": "TestPass123",
            },
        )

        data = json.loads(response.content)
        assert data["redirect"] == "/auth/me/"
