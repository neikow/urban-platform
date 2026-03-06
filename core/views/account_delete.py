from typing import Any, cast

from django import forms
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic.edit import FormView

from core.models import User
from ..widgets import DaisyPasswordInput, DaisyCheckboxInput


class AccountDeleteForm(forms.Form):
    password = forms.CharField(
        required=True,
        label="Mot de passe",
        widget=DaisyPasswordInput("Entrez votre mot de passe pour confirmer"),
        help_text="Pour des raisons de sécurité, veuillez entrer votre mot de passe pour confirmer la suppression de votre compte.",
    )
    confirm = forms.BooleanField(
        required=True,
        label="Je comprends que cette action est irréversible",
        widget=DaisyCheckboxInput(),
        error_messages={
            "required": "Vous devez confirmer que vous comprenez que cette action est irréversible."
        },
    )

    def __init__(self, user: User, *args: Any, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self) -> str:
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Le mot de passe est requis.")

        if not self.user.check_password(password):
            raise forms.ValidationError("Mot de passe incorrect.")

        return password


class AccountDeleteView(LoginRequiredMixin, FormView):
    template_name = "core/account_delete.html"
    form_class = AccountDeleteForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = cast(User, self.request.user)
        return kwargs

    def form_valid(self, form: AccountDeleteForm) -> HttpResponse:
        user = cast(User, self.request.user)
        email = user.email

        # Logout avant la suppression
        logout(self.request)

        # Soft delete le compte pour anonymiser les données
        user.soft_delete()

        messages.success(
            self.request,
            f"Votre compte ({email}) a été supprimé avec succès. Nous espérons vous revoir bientôt.",
        )
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return "/"
