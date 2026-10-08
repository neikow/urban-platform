from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseBase
from django.utils.translation import gettext_lazy as _
from wagtail.admin.views.reports.audit_logging import LogEntriesView


class AuditLogView(LogEntriesView):
    """Settings › Activity log: Wagtail's site history, for administrators.

    Filters by date, user, action, type and name; exports to CSV and Excel with
    the details of each action (core.audit), which Wagtail's export leaves out.
    """

    page_title = _("Activity log")
    index_url_name = "audit_log"
    index_results_url_name = "audit_log_results"
    export_headings = {**LogEntriesView.export_headings, "message": _("Details")}
    list_export = [*LogEntriesView.list_export, "message"]

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user.has_perm("core.view_audit_log"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_filename(self) -> str:
        return super().get_filename().replace("audit-log", "journal-activite")


class AuditLogResultsView(AuditLogView):
    results_only = True
