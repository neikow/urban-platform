from typing import Any

from django.contrib.auth import get_user_model, login
from django.http import HttpResponse
from django.views.generic.edit import FormView
from django import forms

from .auth_mixins import PasswordValidationMixin, EmailValidationMixin

User = get_user_model()


class UserRegistrationForm(PasswordValidationMixin, EmailValidationMixin, forms.Form):
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Mot de passe")
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, required=True, label="Confirmer le mot de passe"
    )
    first_name = forms.CharField(required=True, label="Prénom")
    last_name = forms.CharField(required=True, label="Nom")
    postal_code = forms.CharField(
        required=True,
        label="Code postal",
        max_length=10,
        widget=forms.TextInput(attrs={"placeholder": "13001"}),
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


class RegisterFormView(FormView):
    template_name = "auth/register.html"
    form_class = UserRegistrationForm
    success_url = "/auth/me/"

    def form_valid(self, form: UserRegistrationForm) -> HttpResponse:
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        first_name = form.cleaned_data["first_name"]
        last_name = form.cleaned_data["last_name"]
        postal_code = form.cleaned_data["postal_code"]

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            postal_code=postal_code,
        )

        login(self.request, user)

        return super().form_valid(form)
