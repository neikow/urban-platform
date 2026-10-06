import json
from typing import cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django_ratelimit.decorators import ratelimit

from core.data_export import export_user_data
from core.models import User


@method_decorator(ratelimit(key="user", rate="10/h", method="GET", block=False), name="get")
class DataExportView(LoginRequiredMixin, View):
    """Download every piece of personal data we hold, as JSON (GDPR art. 15 and 20)."""

    def get(self, request: HttpRequest) -> HttpResponse:
        if getattr(request, "limited", False):
            messages.error(request, "Trop de demandes. Réessayez dans une heure.")
            return redirect("me")

        user = cast(User, request.user)
        content = json.dumps(
            export_user_data(user), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2
        )
        filename = f"mes-donnees-{timezone.localdate().isoformat()}.json"
        response = HttpResponse(content, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        return response
