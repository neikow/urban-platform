import json
from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from home.models import HomePage
from home.page_templates import TEMPLATES, get_template


class HomePageTemplatesView(View):
    """Admin: choose a ready-made home page, saved as a draft of the home page."""

    template_name = "home/admin/page_templates.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.page = get_object_or_404(HomePage, pk=kwargs["page_id"])
        if not self.page.permissions_for_user(request.user).can_edit():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, page_id: int) -> HttpResponse:
        return TemplateResponse(
            request, self.template_name, {"page": self.page, "templates": TEMPLATES}
        )

    def post(self, request: HttpRequest, page_id: int) -> HttpResponse:
        template = get_template(request.POST.get("template", ""))
        if template is None:
            raise Http404

        # Start from the latest draft, so its hero (and its photo) is kept.
        draft = self.page.get_latest_revision_as_object()
        draft.content = json.dumps(template.content(list(draft.content.raw_data)))
        draft.save_revision(user=request.user, log_action=True)  # type: ignore[arg-type]

        messages.success(
            request,
            _(
                "The “%(name)s” template is saved as a draft. Edit the texts, preview, then "
                "publish. The previous version stays in the history."
            )
            % {"name": template.name},
        )
        return redirect(reverse("wagtailadmin_pages:edit", args=[self.page.pk]))
