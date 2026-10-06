from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import User
from core.notifications.tokens import read_unsubscribe_token


@method_decorator(csrf_exempt, name="dispatch")
class NotificationUnsubscribeView(View):
    """One-click unsubscribe from a kind of notification, from the link in the email.

    GET asks for confirmation (link scanners must not unsubscribe people);
    POST unsubscribes. POST is CSRF-exempt because mail clients send it
    directly (RFC 8058 List-Unsubscribe-Post); the signed token is the proof.
    """

    template_name = "core/notification_unsubscribe.html"

    def resolve(self, token: str) -> tuple[User, Any] | None:
        data = read_unsubscribe_token(token)
        if data is None:
            return None
        user_uuid, kind = data
        user = User.objects.filter(uuid=user_uuid).first()
        return (user, kind) if user else None

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        resolved = self.resolve(token)
        if resolved is None:
            return render(request, self.template_name, {"invalid": True}, status=400)
        _user, kind = resolved
        return render(request, self.template_name, {"kind": kind, "done": False})

    def post(self, request: HttpRequest, token: str) -> HttpResponse:
        resolved = self.resolve(token)
        if resolved is None:
            return render(request, self.template_name, {"invalid": True}, status=400)
        user, kind = resolved
        setattr(user, kind.preference_field, False)
        user.save(update_fields=[kind.preference_field])
        return render(request, self.template_name, {"kind": kind, "done": True})
