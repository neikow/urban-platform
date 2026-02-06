from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic.edit import FormView
from django import forms
from django.contrib import messages
from core.emails.tasks import send_verification_email

from .auth_mixins import PasswordValidationMixin
from ..widgets import DaisyTextInput, DaisyPasswordInput, DaisyEmailInput, DaisyCheckboxInput
from core.models import User


class ProfileUpdateForm(forms.Form):
    email = forms.EmailField(
        required=True, label="Email", widget=DaisyEmailInput(placeholder="jean.dupont@email.fr")
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
    phone_number = forms.CharField(
        required=False,
        label="Téléphone",
        max_length=20,
        widget=DaisyTextInput(placeholder="06 12 34 56 78"),
    )
    newsletter_subscription = forms.BooleanField(
        required=False,
        label="Je souhaite être informé(e) des actualités et des événements par email",
        widget=DaisyCheckboxInput(),
    )

    def __init__(self, user: User, *args: Any, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

        if not kwargs.get("data"):
            self.initial = {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "postal_code": user.postal_code,
                "phone_number": user.phone_number,
                "newsletter_subscription": user.newsletter_subscription,
            }

    def clean_email(self) -> str:
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email invalide.")

        if email != self.user.email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")

        return email

    def clean_postal_code(self) -> str:
        postal_code = str(self.cleaned_data.get("postal_code"))
        if not postal_code:
            raise forms.ValidationError("Le code postal est requis.")
        if not postal_code.isdigit():
            raise forms.ValidationError("Le code postal doit contenir uniquement des chiffres.")
        if len(postal_code) != 5:
            raise forms.ValidationError("Le code postal doit contenir exactement 5 chiffres.")
        return postal_code


class PasswordChangeForm(PasswordValidationMixin, forms.Form):
    current_password = forms.CharField(
        required=True,
        label="Mot de passe actuel",
        widget=DaisyPasswordInput("••••••••"),
    )
    new_password = forms.CharField(
        required=True,
        label="Nouveau mot de passe",
        widget=DaisyPasswordInput("••••••••"),
    )
    confirm_password = forms.CharField(
        required=True,
        label="Confirmer le nouveau mot de passe",
        widget=DaisyPasswordInput("••••••••"),
        help_text="Minimum 8 caractères, 1 majuscule et 1 chiffre",
    )

    def __init__(self, user: User, *args: Any, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self) -> str:
        current_password = self.cleaned_data.get("current_password")
        if not current_password:
            raise forms.ValidationError("Le mot de passe actuel est requis.")

        if not self.user.check_password(current_password):
            raise forms.ValidationError("Le mot de passe actuel est incorrect.")

        return current_password

    def clean_new_password(self) -> str:
        new_password = self.cleaned_data.get("new_password")
        if not new_password:
            raise forms.ValidationError("Le nouveau mot de passe est requis.")
        self.validate_password_strength(new_password)
        return new_password

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if not cleaned_data:
            return None

        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Les nouveaux mots de passe ne correspondent pas.")

        return cleaned_data


class ProfileEditView(LoginRequiredMixin, FormView):
    template_name = "core/profile_edit.html"
    form_class = ProfileUpdateForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = cast(User, self.request.user)
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["password_form"] = PasswordChangeForm(user=cast(User, self.request.user))
        return context

    def form_valid(self, form: ProfileUpdateForm) -> HttpResponse:
        user = cast(User, self.request.user)

        email_changed = form.cleaned_data["email"] != user.email

        user.email = form.cleaned_data["email"]
        user.first_name = form.cleaned_data["first_name"]
        user.last_name = form.cleaned_data["last_name"]
        user.postal_code = form.cleaned_data["postal_code"]
        user.phone_number = form.cleaned_data.get("phone_number", "")
        user.newsletter_subscription = form.cleaned_data.get("newsletter_subscription", False)

        if email_changed:
            user.is_verified = False
            send_verification_email.delay(user.pk)  # type: ignore[attr-defined]
            messages.warning(
                self.request,
                "Votre email a été modifié. Vous devrez le vérifier à nouveau.",
            )

        user.save()

        messages.success(self.request, "Votre profil a été mis à jour avec succès.")
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse("me")


class PasswordChangeView(LoginRequiredMixin, FormView):
    template_name = "core/profile_edit.html"
    form_class = PasswordChangeForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = cast(User, self.request.user)
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["form"] = ProfileUpdateForm(user=cast(User, self.request.user))
        context["password_form"] = self.get_form()
        return context

    def form_valid(self, form: PasswordChangeForm) -> HttpResponse:
        user = cast(User, self.request.user)
        user.set_password(form.cleaned_data["new_password"])
        user.save()

        messages.success(
            self.request,
            "Votre mot de passe a été modifié avec succès. Veuillez vous reconnecter.",
        )
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse("login")
