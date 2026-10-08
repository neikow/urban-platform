from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from core import task_monitor
from core.models import UserRole

# How often the page refreshes the task lists, in milliseconds.
POLL_INTERVAL_MS = 4000


def can_manage_tasks(request: HttpRequest) -> bool:
    user = request.user
    return user.is_authenticated and (
        user.is_superuser or getattr(user, "role", None) == UserRole.ADMIN
    )


def _check(request: HttpRequest) -> None:
    if not can_manage_tasks(request):
        raise PermissionDenied


def status_context() -> dict[str, Any]:
    return {"live": task_monitor.live_state(), "runs": task_monitor.recent_runs()}


class TasksView(WagtailAdminTemplateMixin, TemplateView):
    template_name = "core/admin/tasks.html"
    page_title = gettext_lazy("Tasks")
    header_icon = "cogs"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        _check(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(status_context())
        context["triggers"] = task_monitor.TRIGGERS
        context["status_url"] = reverse("admin_tasks_status")
        context["poll_interval"] = POLL_INTERVAL_MS
        return context


@never_cache
@require_GET
def tasks_status(request: HttpRequest) -> HttpResponse:
    """The task lists alone, polled by the page (frontend/src/admin/tasks.ts)."""
    _check(request)
    return render(request, "core/admin/tasks_status.html", status_context())


@require_POST
def run_task(request: HttpRequest, key: str) -> HttpResponseRedirect:
    _check(request)
    trigger = task_monitor.get_trigger(key)
    if trigger is None:
        raise Http404(key)
    if trigger.start():
        messages.success(request, _("“%(task)s” has started.") % {"task": trigger.label})
    else:
        messages.warning(request, _("“%(task)s” is already in progress.") % {"task": trigger.label})
    return HttpResponseRedirect(reverse("admin_tasks"))
