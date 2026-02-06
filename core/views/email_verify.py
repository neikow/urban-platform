from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from core.emails.tokens import verify_verification_token

User = get_user_model()


class EmailVerifyView(View):
    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        user_id = verify_verification_token(token)

        if user_id is None:
            return redirect("email_verify_error")

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return redirect("email_verify_error")

        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])

        return redirect("email_verify_success")


class EmailVerifySuccessView(TemplateView):
    template_name = "auth/email_verify_success.html"


class EmailVerifyErrorView(TemplateView):
    template_name = "auth/email_verify_error.html"
