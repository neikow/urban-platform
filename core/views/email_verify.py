from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from core.emails.tasks import send_verification_email
from core.emails.tokens import verify_verification_token

User = get_user_model()


class EmailVerifyView(View):
    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        user_uuid = verify_verification_token(token)

        if user_uuid is None:
            return redirect("email_verify_error")

        try:
            user = User.objects.get(uuid=user_uuid)
        except User.DoesNotExist:
            return redirect("email_verify_error")

        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])

        return redirect("email_verify_success")


@method_decorator(ratelimit(key="user", rate="3/h", method="POST", block=False), name="post")
class EmailVerifyResendView(LoginRequiredMixin, View):
    """Send a new verification link to the signed-in user."""

    def post(self, request: HttpRequest) -> HttpResponse:
        user = request.user

        if getattr(request, "limited", False):
            messages.error(
                request,
                "Trop de demandes. Patientez avant de demander un nouveau lien de vérification.",
            )
        elif user.is_verified:  # type: ignore[union-attr]
            messages.info(request, "Votre adresse email est déjà vérifiée.")
        else:
            send_verification_email.delay(user.pk)  # type: ignore[attr-defined]
            messages.success(
                request,
                f"Un nouveau lien de vérification a été envoyé à {user.email}.",  # type: ignore[union-attr]
            )

        next_url = request.POST.get("next")
        if not next_url or not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "me"
        return redirect(next_url)


class EmailVerifySuccessView(TemplateView):
    template_name = "auth/email_verify_success.html"


class EmailVerifyErrorView(TemplateView):
    template_name = "auth/email_verify_error.html"
