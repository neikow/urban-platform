"""Settings › Neighborhood associations › Import: the CIQ of one federation from a CSV file.

The import itself is core.association_import. Sending the file shows a
preview (nothing saved); confirming it imports the same rows, kept in the
session in between and dropped once used: the file itself is not stored (it
holds personal contacts). It runs during the request: a federation holds a few
dozen CIQ, each address looked up in at most a few seconds.
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBase, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.generic import FormView
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from core.association_import import (
    AssociationImportError,
    ImportReport,
    import_associations,
    read_rows,
)
from core.audit import audit

MAX_UPLOAD_SIZE = 2 * 1024**2
# The previewed rows and federation, until the import is confirmed.
SESSION_KEY = "association_import"


def can_import_associations(request: HttpRequest) -> bool:
    return request.user.has_perms(
        ["core.add_neighborhoodassociation", "core.change_neighborhoodassociation"]
    )


class AssociationImportForm(forms.Form):
    file = forms.FileField(
        label=gettext_lazy("CSV file"),
        help_text=gettext_lazy(
            "A copy of the Confédération's directory, in UTF-8, with the columns code, name, "
            "address, contact_email, contact_phone and website (only code and name are required)."
        ),
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
    )
    federation = forms.IntegerField(
        label=gettext_lazy("Federation"),
        help_text=gettext_lazy(
            "Only its CIQ are imported: 7 imports the codes 701 to 799 (the 7th arrondissement)."
        ),
        min_value=1,
        max_value=99,
    )

    def clean_file(self) -> list[dict[str, str]]:
        upload = self.cleaned_data["file"]
        if upload.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(_("The file is too large."))
        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise forms.ValidationError(_("The file is not encoded in UTF-8.")) from error
        try:
            return read_rows(text.splitlines())
        except AssociationImportError as error:
            raise forms.ValidationError(str(error)) from error


class AssociationImportView(WagtailAdminTemplateMixin, FormView):
    template_name = "core/admin/association_import.html"
    page_title = gettext_lazy("Import neighborhood associations")
    header_icon = "group"
    form_class = AssociationImportForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not can_import_associations(request):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["index_url"] = reverse("neighborhood_association:index")
        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if "confirm" in request.POST:
            return self.confirm()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: AssociationImportForm) -> HttpResponse:
        rows, federation = form.cleaned_data["file"], form.cleaned_data["federation"]
        try:
            report = import_associations(rows, federation, dry_run=True)
        except AssociationImportError as error:
            form.add_error("file", str(error))
            return self.form_invalid(form)
        self.request.session[SESSION_KEY] = {"rows": rows, "federation": federation}
        return self.render_to_response(
            self.get_context_data(form=form, report=report, federation=federation, preview=True)
        )

    def confirm(self) -> HttpResponse:
        pending = self.request.session.pop(SESSION_KEY, None)
        if pending is None:
            messages.error(self.request, _("Nothing to import: send the file again."))
            return HttpResponseRedirect(reverse("association_import"))
        try:
            report = import_associations(pending["rows"], pending["federation"])
        except AssociationImportError as error:
            messages.error(self.request, str(error))
            return HttpResponseRedirect(reverse("association_import"))
        self.log(report)
        messages.success(
            self.request,
            _("%(created)d created, %(updated)d updated.")
            % {"created": len(report.created), "updated": len(report.updated)},
        )
        return self.render_to_response(
            self.get_context_data(report=report, federation=pending["federation"], preview=False)
        )

    def log(self, report: ImportReport) -> None:
        for association in report.created:
            audit(association, "wagtail.create", user=self.request.user)
        for association in report.updated:
            audit(association, "wagtail.edit", user=self.request.user)
