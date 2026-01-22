import json
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.views.login import LoginForm

User = get_user_model()


@pytest.mark.django_db
class TestLoginForm:
    def test_form_valid_with_correct_credentials(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="TestPass123",
            first_name="Test",
            last_name="User",
        )

        form = LoginForm(
            data={
                "email": "testuser@example.com",
                "password": "TestPass123",
            }
        )

        assert form.is_valid()
        assert "user" in form.cleaned_data
        assert form.cleaned_data["user"] == user

    def test_form_invalid_with_wrong_password(self):
        User.objects.create_user(
            email="testuser@example.com",
            password="CorrectPass123",
            first_name="Test",
            last_name="User",
        )

        form = LoginForm(
            data={
                "email": "testuser@example.com",
                "password": "WrongPass123",
            }
        )

        assert not form.is_valid()
        assert "__all__" in form.errors
        assert "Email ou mot de passe incorrect" in str(form.errors["__all__"])

    def test_form_invalid_with_nonexistent_email(self):
        """Test that form is invalid with non-existent email."""
        form = LoginForm(
            data={
                "email": "nonexistent@example.com",
                "password": "TestPass123",
            }
        )

        assert not form.is_valid()
        assert "__all__" in form.errors
        assert "Email ou mot de passe incorrect" in str(form.errors["__all__"])

    def test_form_invalid_without_email(self):
        """Test that form is invalid without email."""
        form = LoginForm(
            data={
                "password": "TestPass123",
            }
        )

        assert not form.is_valid()
        assert "email" in form.errors

    def test_form_invalid_without_password(self):
        """Test that form is invalid without password."""
        form = LoginForm(
            data={
                "email": "testuser@example.com",
            }
        )

        assert not form.is_valid()
        assert "password" in form.errors

    def test_form_invalid_with_invalid_email_format(self):
        """Test that form is invalid with invalid email format."""
        form = LoginForm(
            data={
                "email": "not-an-email",
                "password": "TestPass123",
            }
        )

        assert not form.is_valid()
        assert "email" in form.errors

    def test_form_invalid_with_empty_data(self):
        """Test that form is invalid with empty data."""
        form = LoginForm(data={})

        assert not form.is_valid()
        assert "email" in form.errors
        assert "password" in form.errors

    def test_form_labels(self):
        """Test that form has correct labels."""
        form = LoginForm()

        assert form.fields["email"].label == "Email"
        assert form.fields["password"].label == "Mot de passe"

    def test_form_required_fields(self):
        """Test that required fields are marked as required."""
        form = LoginForm()

        assert form.fields["email"].required is True
        assert form.fields["password"].required is True

    def test_form_password_widget_is_password_input(self):
        """Test that password field uses PasswordInput widget."""
        from django.forms.widgets import PasswordInput

        form = LoginForm()

        assert isinstance(form.fields["password"].widget, PasswordInput)


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
