from typing import Any

from django.contrib.auth import authenticate, login as auth_login
from django.http import HttpRequest, HttpResponse
from django.views import View
from django import forms

from .auth_mixins import JsonResponseMixin
from ..widgets import DaisyEmailInput, DaisyPasswordInput


class LoginForm(forms.Form):
    email = forms.EmailField(
        required=True, label="Email", widget=DaisyEmailInput("jean.dupont@email.fr")
    )
    password = forms.CharField(
        widget=DaisyPasswordInput(placeholder="••••••••"), required=True, label="Mot de passe"
    )

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if not cleaned_data:
            return None

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError("Email ou mot de passe incorrect.")
            cleaned_data["user"] = user

        return cleaned_data


class LoginView(JsonResponseMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        form = LoginForm(request.POST)

        if form.is_valid():
            user = form.cleaned_data["user"]
            auth_login(request, user)
            return self.json_success_response("/auth/me/")

        return self.json_error_response(form)
