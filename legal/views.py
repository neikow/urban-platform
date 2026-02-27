import typing
from typing import Any

from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponseBase, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView

from core.utils import get_client_ip
from legal.forms import CodeOfConductConsentForm
from legal.models import CodeOfConductPage
from legal.utils import has_valid_code_of_conduct_consent, create_code_of_conduct_consent_record

if typing.TYPE_CHECKING:
    from core.models.user import User
else:
    User = get_user_model()


class CodeOfConductConsentView(FormView):
    template_name = "legal/code_of_conduct_consent.html"
    form_class = CodeOfConductConsentForm

    user: User

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user or not request.user.is_authenticated:
            return redirect("login")

        self.user = request.user

        if has_valid_code_of_conduct_consent(self.user):
            return redirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: CodeOfConductConsentForm) -> HttpResponse:
        create_code_of_conduct_consent_record(
            user=self.user,
            consent_ip=get_client_ip(self.request),
        )

        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["next"] = self.request.POST.get("next") or self.request.GET.get("next")

        code_of_conduct_page: CodeOfConductPage = CodeOfConductPage.objects.live().first()
        page_content = code_of_conduct_page.content if code_of_conduct_page else ""

        context["content"] = page_content

        return context

    def get_success_url(self) -> str:
        redirect_to = self.request.POST.get("next") or self.request.GET.get("next")

        if redirect_to and url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return redirect_to

        return reverse("me")
