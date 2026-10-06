from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from publications.models import PollClosureReason, ProjectPage
from publications.polls import close_poll


class ClosePollView(View):
    """Admin action: close a project's poll now and email the results."""

    template_name = "publications/admin/close_poll_confirm.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.project = get_object_or_404(ProjectPage, pk=kwargs["project_id"])
        if not self.project.permissions_for_user(request.user).can_publish():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        return TemplateResponse(request, self.template_name, {"project": self.project})

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if self.project.is_voting_open:
            close_poll(self.project, PollClosureReason.MANUAL, closed_by=request.user)  # type: ignore[arg-type]
            messages.success(
                request,
                _(
                    "The poll on “%(title)s” is closed. Results are being sent to voters who opted in."
                )
                % {"title": self.project.title},
            )
        else:
            messages.info(request, _("This poll was already closed."))
        return redirect(reverse("wagtailadmin_pages:edit", args=[self.project.pk]))
