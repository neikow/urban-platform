from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
import pytest

from core.views.register import UserRegistrationForm
from core.views.register import RegisterFormView

VALID_REQUEST = {
    "email": "testuser@example.com",
    "password": "Password123",
    "confirm_password": "Password123",
    "first_name": "Test",
    "last_name": "User",
    "postal_code": "13001",
    "accept_terms": True,
}

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistrationForm:
    def test_form_valid_with_all_correct_data(self):
        form = UserRegistrationForm(data=VALID_REQUEST)

        assert form.is_valid()
        assert form.cleaned_data["email"] == "testuser@example.com"
        assert form.cleaned_data["first_name"] == "Test"
        assert form.cleaned_data["last_name"] == "User"
        assert form.cleaned_data["postal_code"] == "13001"

    def test_form_invalid_with_duplicate_email(self):
        User.objects.create_user(email="testuser@example.com", password="Password123")

        form = UserRegistrationForm(data=VALID_REQUEST)

        assert not form.is_valid()
        assert "email" in form.errors
        assert "déjà utilisé" in str(form.errors["email"])

    def test_form_invalid_with_password_mismatch(self):
        data = VALID_REQUEST.copy()
        data["confirm_password"] = "DifferentPassword123"

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "__all__" in form.errors
        assert "ne correspondent pas" in str(form.errors["__all__"])

    def test_form_invalid_with_weak_password(self):
        data = VALID_REQUEST.copy()
        data["password"] = "weak"
        data["confirm_password"] = "weak"

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "password" in form.errors
        assert "8 caractères" in str(form.errors["password"])

    def test_form_invalid_without_uppercase_in_password(self):
        data = VALID_REQUEST.copy()
        data["password"] = "password123"
        data["confirm_password"] = "password123"

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "password" in form.errors
        assert "majuscule" in str(form.errors["password"])

    def test_form_invalid_without_digit_in_password(self):
        data = VALID_REQUEST.copy()
        data["password"] = "PasswordABC"
        data["confirm_password"] = "PasswordABC"

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "password" in form.errors
        assert "chiffre" in str(form.errors["password"])

    def test_form_invalid_without_accepting_terms(self):
        data = VALID_REQUEST.copy()
        data["accept_terms"] = False

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "accept_terms" in form.errors

    def test_form_invalid_with_missing_email(self):
        data = VALID_REQUEST.copy()
        del data["email"]

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "email" in form.errors

    def test_form_invalid_with_invalid_email_format(self):
        data = VALID_REQUEST.copy()
        data["email"] = "not-an-email"

        form = UserRegistrationForm(data=data)

        assert not form.is_valid()
        assert "email" in form.errors

    def test_form_invalid_with_missing_required_fields(self):
        form = UserRegistrationForm(data={})

        assert not form.is_valid()
        assert "email" in form.errors
        assert "password" in form.errors
        assert "first_name" in form.errors
        assert "last_name" in form.errors
        assert "postal_code" in form.errors
        assert "accept_terms" in form.errors

    def test_form_labels(self):
        form = UserRegistrationForm()

        assert form.fields["email"].label == "Email"
        assert form.fields["password"].label == "Mot de passe"
        assert form.fields["confirm_password"].label == "Confirmer le mot de passe"
        assert form.fields["first_name"].label == "Prénom"
        assert form.fields["last_name"].label == "Nom"
        assert form.fields["postal_code"].label == "Code postal"

    def test_form_required_fields(self):
        form = UserRegistrationForm()

        assert form.fields["email"].required is True
        assert form.fields["password"].required is True
        assert form.fields["confirm_password"].required is True
        assert form.fields["first_name"].required is True
        assert form.fields["last_name"].required is True
        assert form.fields["postal_code"].required is True
        assert form.fields["accept_terms"].required is True

    def test_form_password_widgets_are_password_input(self):
        from django.forms.widgets import PasswordInput

        form = UserRegistrationForm()

        assert isinstance(form.fields["password"].widget, PasswordInput)
        assert isinstance(form.fields["confirm_password"].widget, PasswordInput)


class TestUserRegistrationView:
    @pytest.mark.django_db
    @patch("core.views.register.UserRegistrationForm")
    def test_registration_view_creates_user_and_sends_verification_email(self, mock_form_class):
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = VALID_REQUEST
        mock_form_class.return_value = mock_form

        with patch("core.emails.tasks.send_verification_email.delay") as mock_send_email:
            view = RegisterFormView()
            request = MagicMock()
            view.request = request
            response = view.form_valid(mock_form)

            assert response.status_code == 302  # Redirect after successful registration
            assert User.objects.filter(email=VALID_REQUEST["email"]).exists()
            user = User.objects.get(email=VALID_REQUEST["email"])
            mock_send_email.assert_called_once_with(user.pk)
