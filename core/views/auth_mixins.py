from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django import forms
from django.http import JsonResponse

from core.models import Territory

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


class AddressFieldMixin:
    """Optional home address, located in the territory's city to attach the user to an association.

    After validation, ``address_location`` holds its GeoJSON point, or None when it
    is empty or the geocoding service is down (the address is then kept unlocated).
    """

    address_location: dict | None = None
    cleaned_data: dict

    def clean_address(self) -> str:
        from core.geocoding import GeocodingUnavailable, geocode

        address = " ".join(self.cleaned_data.get("address", "").split())
        self.address_location = None
        if not address:
            return ""
        try:
            found = geocode(address)
        except GeocodingUnavailable:
            return address
        if found is None:
            city = Territory.current().city_name
            where = f" à {city}" if city else ""
            raise forms.ValidationError(
                f"Adresse introuvable{where}. Choisissez-la dans la liste, "
                "ou laissez ce champ vide si vous habitez ailleurs."
            )
        self.address_location = found.point
        return found.label
