import typing

from django import forms
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseBase
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from core.emails.tasks import send_password_reset_email
from core.emails.tokens import verify_password_reset_token
from core.views.auth_mixins import PasswordValidationMixin
from core.widgets import DaisyEmailInput, DaisyPasswordInput

if typing.TYPE_CHECKING:
    from core.models import User
else:
    User = get_user_model()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=DaisyEmailInput(placeholder="jean.dupont@email.fr"),
    )


class PasswordResetRequestView(FormView):
    template_name = "auth/password_reset_request.html"
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy("password_reset_sent")

    def form_valid(self, form: PasswordResetRequestForm) -> HttpResponse:
        email = form.cleaned_data["email"]

        try:
            user = User.objects.get(email=email)
            send_password_reset_email.delay(user.pk)  # type: ignore[attr-defined]
        except User.DoesNotExist:
            # Prevent user enumeration
            pass

        return super().form_valid(form)


class PasswordResetSentView(TemplateView):
    template_name = "auth/password_reset_sent.html"


class PasswordResetConfirmForm(PasswordValidationMixin, forms.Form):
    password = forms.CharField(
        required=True,
        label="Nouveau mot de passe",
        widget=DaisyPasswordInput("••••••••"),
    )
    confirm_password = forms.CharField(
        required=True,
        label="Confirmer le mot de passe",
        widget=DaisyPasswordInput("••••••••"),
        help_text="Minimum 8 caractères, 1 majuscule et 1 chiffre",
    )

    def clean(self) -> dict[str, typing.Any] | None:
        cleaned_data = super().clean()
        if not cleaned_data:
            return None

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")

        return cleaned_data

    def clean_password(self) -> str:
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Le mot de passe est requis.")
        self.validate_password_strength(password)
        return password


class PasswordResetConfirmView(FormView):
    template_name = "auth/password_reset_confirm.html"
    form_class = PasswordResetConfirmForm

    token: str
    reset_user: "User | None" = None

    def dispatch(
        self, request: typing.Any, *args: typing.Any, **kwargs: typing.Any
    ) -> HttpResponseBase:
        self.token = kwargs.get("token", "")
        user_uuid = verify_password_reset_token(self.token)

        if user_uuid is None:
            return redirect("password_reset_error")

        try:
            self.reset_user = User.objects.get(uuid=user_uuid)
        except User.DoesNotExist:
            return redirect("password_reset_error")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: PasswordResetConfirmForm) -> HttpResponse:
        if self.reset_user:
            password = form.cleaned_data["password"]
            self.reset_user.set_password(password)
            self.reset_user.save(update_fields=["password"])

        return redirect("password_reset_complete")


class PasswordResetErrorView(TemplateView):
    template_name = "auth/password_reset_error.html"


class PasswordResetCompleteView(TemplateView):
    template_name = "auth/password_reset_complete.html"
