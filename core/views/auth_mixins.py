from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django import forms
from django.http import JsonResponse

User = get_user_model()


class PasswordValidationMixin:
    @staticmethod
    def validate_password_strength(password: str, user: AbstractBaseUser | None = None) -> None:
        if not password:
            raise forms.ValidationError("Le mot de passe est requis.")

        if (
            len(password) < 8
            or not any(char.isdigit() for char in password)
            or not any(char.isupper() for char in password)
        ):
            raise forms.ValidationError(
                "Le mot de passe doit contenir au moins 8 caractères, une lettre majuscule et un chiffre."
            )

        # Also enforce Django's AUTH_PASSWORD_VALIDATORS (common-password,
        # user-attribute similarity, numeric-only…), which the custom rules above
        # do not cover. Raises django.core.exceptions.ValidationError, which forms
        # handle like forms.ValidationError.
        validate_password(password, user)  # type: ignore[arg-type]  # custom user model


class EmailValidationMixin:
    @staticmethod
    def validate_email_unique(email: str) -> str:
        if not email or not isinstance(email, str):
            raise forms.ValidationError("Email invalide.")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email déjà utilisé.")

        return email


class JsonResponseMixin:
    @staticmethod
    def json_error_response(form: forms.Form, status: int = 400) -> JsonResponse:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(e) for e in error_list]

        return JsonResponse({"success": False, "errors": errors}, status=status)

    @staticmethod
    def json_success_response(redirect_url: str) -> JsonResponse:
        return JsonResponse({"success": True, "redirect": redirect_url})
