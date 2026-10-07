import json
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from wagtail.models import Page

from core.page_templates import get_template, templates_for

TEMPLATE_NAME = "core/admin/page_templates.html"


def creation_chooser(
    request: HttpRequest, parent_page: Page, page_class: type[Page]
) -> HttpResponse:
    """Shown before the editor of a new page: pick a template or start blank."""

    def create_url(**query: str) -> str:
        url = reverse(
            "wagtailadmin_pages:add",
            args=[page_class._meta.app_label, page_class._meta.model_name, parent_page.pk],
        )
        return f"{url}?{urlencode({**request.GET.dict(), **query})}"

    return TemplateResponse(
        request,
        TEMPLATE_NAME,
        {
            "title": _("New %(page_type)s") % {"page_type": page_class._meta.verbose_name},
            "subtitle": parent_page.title,
            "intro": _("Start from a template and adapt it, or from a blank page."),
            "templates": [
                {
                    "template": template,
                    "outline": template.outline(page_class),
                    "url": create_url(template=template.slug),
                }
                for template in templates_for(page_class)
            ],
            "blank_url": create_url(blank="1"),
            "cancel_url": reverse("wagtailadmin_explore", args=[parent_page.pk]),
        },
    )


class PageTemplatesView(View):
    """Admin: replace the content of an existing page with a template, as a draft."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.page = get_object_or_404(Page, pk=kwargs["page_id"]).specific
        if not templates_for(type(self.page)):
            raise Http404
        if not self.page.permissions_for_user(request.user).can_edit():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, page_id: int) -> HttpResponse:
        page_class = type(self.page)
        return TemplateResponse(
            request,
            TEMPLATE_NAME,
            {
                "title": _("Start from a template"),
                "subtitle": self.page.title,
                "intro": _(
                    "The template replaces the content of the page in a new draft. Nothing "
                    "changes on the website until you publish, and the current version stays "
                    "in the page history."
                ),
                "templates": [
                    {"template": template, "outline": template.outline(page_class)}
                    for template in templates_for(page_class)
                ],
                "cancel_url": reverse("wagtailadmin_pages:edit", args=[self.page.pk]),
            },
        )

    def post(self, request: HttpRequest, page_id: int) -> HttpResponse:
        template = get_template(type(self.page), request.POST.get("template", ""))
        if template is None:
            raise Http404

        # Start from the latest draft, so the blocks the template keeps come from it.
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
