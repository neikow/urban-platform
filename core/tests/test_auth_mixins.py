import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from core.views.auth_mixins import (
    PasswordValidationMixin,
    EmailValidationMixin,
    JsonResponseMixin,
)

User = get_user_model()


class TestPasswordValidationMixin:
    """Tests for PasswordValidationMixin."""

    def test_validate_password_strength_valid_password(self):
        valid_password = "ValidPass123"
        # Should not raise any exception
        PasswordValidationMixin.validate_password_strength(valid_password)

    def test_validate_password_strength_too_short(self):
        short_password = "Pass1"
        with pytest.raises(forms.ValidationError) as exc_info:
            PasswordValidationMixin.validate_password_strength(short_password)
        assert "8 caractères" in str(exc_info.value)

    def test_validate_password_strength_no_uppercase(self):
        no_uppercase = "validpass123"
        with pytest.raises(forms.ValidationError) as exc_info:
            PasswordValidationMixin.validate_password_strength(no_uppercase)
        assert "majuscule" in str(exc_info.value)

    def test_validate_password_strength_no_digit(self):
        no_digit = "ValidPassword"
        with pytest.raises(forms.ValidationError) as exc_info:
            PasswordValidationMixin.validate_password_strength(no_digit)
        assert "chiffre" in str(exc_info.value)

    def test_validate_password_strength_empty_password(self):
        with pytest.raises(forms.ValidationError) as exc_info:
            PasswordValidationMixin.validate_password_strength("")
        assert "requis" in str(exc_info.value)

    def test_validate_password_strength_none_password(self):
        with pytest.raises(forms.ValidationError) as exc_info:
            PasswordValidationMixin.validate_password_strength(None)
        assert "requis" in str(exc_info.value)


@pytest.mark.django_db
class TestEmailValidationMixin:
    def test_validate_email_unique_valid_email(self):
        email = "newuser@example.com"
        result = EmailValidationMixin.validate_email_unique(email)
        assert result == email

    def test_validate_email_unique_duplicate_email(self):
        email = "existing@example.com"
        User.objects.create_user(email=email, password="TestPass123")

        with pytest.raises(forms.ValidationError) as exc_info:
            EmailValidationMixin.validate_email_unique(email)
        assert "déjà utilisé" in str(exc_info.value)

    def test_validate_email_unique_empty_email(self):
        with pytest.raises(forms.ValidationError) as exc_info:
            EmailValidationMixin.validate_email_unique("")
        assert "invalide" in str(exc_info.value)

    def test_validate_email_unique_none_email(self):
        with pytest.raises(forms.ValidationError) as exc_info:
            EmailValidationMixin.validate_email_unique(None)
        assert "invalide" in str(exc_info.value)

    def test_validate_email_unique_non_string_email(self):
        with pytest.raises(forms.ValidationError) as exc_info:
            EmailValidationMixin.validate_email_unique(123)
        assert "invalide" in str(exc_info.value)


class TestJsonResponseMixin:
    def test_json_error_response_with_field_errors(self):
        class TestForm(forms.Form):
            email = forms.EmailField()
            password = forms.CharField()

        form = TestForm(data={"email": "invalid", "password": ""})
        form.is_valid()

        response = JsonResponseMixin.json_error_response(form)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 400

        import json

        content = json.loads(response.content)
        assert content["success"] is False
        assert "errors" in content
        assert "email" in content["errors"] or "password" in content["errors"]

    def test_json_error_response_with_non_field_errors(self):
        class TestForm(forms.Form):
            def clean(self):
                raise forms.ValidationError("Global error")

        form = TestForm(data={})
        form.is_valid()

        response = JsonResponseMixin.json_error_response(form)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 400

        import json

        content = json.loads(response.content)
        assert content["success"] is False
        assert "__all__" in content["errors"]

    def test_json_error_response_custom_status(self):
        class TestForm(forms.Form):
            email = forms.EmailField()

        form = TestForm(data={"email": "invalid"})
        form.is_valid()

        response = JsonResponseMixin.json_error_response(form, status=422)
        assert response.status_code == 422

    def test_json_success_response(self):
        redirect_url = "/auth/me/"
        response = JsonResponseMixin.json_success_response(redirect_url)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 200

        import json

        content = json.loads(response.content)
        assert content["success"] is True
        assert content["redirect"] == redirect_url
