import typing
from typing import Any

from django.contrib.auth import get_user_model, login
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic.edit import FormView
from django import forms

from core.emails.tasks import send_verification_email
from legal.utils import has_valid_code_of_conduct_consent
from .auth_mixins import PasswordValidationMixin, EmailValidationMixin
from ..widgets import DaisyTextInput, DaisyPasswordInput, DaisyEmailInput

if typing.TYPE_CHECKING:
    from core.models import User
else:
    User = get_user_model()


class UserRegistrationForm(PasswordValidationMixin, EmailValidationMixin, forms.Form):
    email = forms.EmailField(
        required=True, label="Email", widget=DaisyEmailInput(placeholder="jean.dupont@email.fr")
    )
    password = forms.CharField(
        required=True,
        label="Mot de passe",
        widget=DaisyPasswordInput("••••••••"),
    )
    confirm_password = forms.CharField(
        required=True,
        label="Confirmer le mot de passe",
        widget=DaisyPasswordInput("••••••••"),
        help_text="Minimum 8 caractères, 1 majuscule et 1 chiffre",
    )
    first_name = forms.CharField(
        required=True, label="Prénom", widget=DaisyTextInput(placeholder="Jean")
    )
    last_name = forms.CharField(
        required=True, label="Nom", widget=DaisyTextInput(placeholder="Dupont")
    )
    postal_code = forms.CharField(
        required=True,
        label="Code postal",
        max_length=10,
        widget=DaisyTextInput(placeholder="13001"),
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="J'accepte la charte de bonne conduite et les conditions d'utilisation",
        error_messages={
            "required": "Vous devez accepter la charte de bonne conduite et les conditions d'utilisation pour vous inscrire."
        },
    )

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if not cleaned_data:
            return None

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")

        return cleaned_data

    def clean_email(self) -> str:
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email invalide.")
        return self.validate_email_unique(email)

    def clean_password(self) -> str:
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Le mot de passe est requis.")
        self.validate_password_strength(password)
        return password

    def clean_postal_code(self) -> str:
        postal_code = str(self.cleaned_data.get("postal_code"))
        if not postal_code:
            raise forms.ValidationError("Le code postal est requis.")
        if not postal_code.isdigit():
            raise forms.ValidationError("Le code postal doit contenir uniquement des chiffres.")
        if len(postal_code) != 5:
            raise forms.ValidationError("Le code postal doit contenir exactement 5 chiffres.")
        return postal_code


class RegisterFormView(FormView):
    template_name = "auth/register.html"
    form_class = UserRegistrationForm

    user: User

    def form_valid(self, form: UserRegistrationForm) -> HttpResponse:
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        first_name = form.cleaned_data["first_name"]
        last_name = form.cleaned_data["last_name"]
        postal_code = form.cleaned_data["postal_code"]

        self.user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            postal_code=postal_code,
        )

        send_verification_email.delay(self.user.pk)  # type: ignore[attr-defined]

        login(self.request, self.user)

        return super().form_valid(form)

    def get_success_url(self) -> str:
        if not has_valid_code_of_conduct_consent(self.user):
            return reverse("code_of_conduct_consent")

        return reverse("me")
