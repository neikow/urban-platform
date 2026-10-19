"""Settings › Content transfer: export the content here, import it elsewhere (superusers)."""

from typing import Any, cast

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpRequest, HttpResponseBase, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import FormView

from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from core.audit import audit
from core.content_transfer.archive import ArchiveError, open_archive
from core.content_transfer.importer import ImportMode
from core.models import ContentTransfer, ContentTransferKind, ContentTransferStatus, User

RECENT_JOBS = 20
# Larger archives are refused at upload (nginx allows a little more).
MAX_UPLOAD_SIZE = 2 * 1024**3


def can_transfer_content(request: HttpRequest) -> bool:
    user = request.user
    return bool(user.is_authenticated and user.is_active and user.is_superuser)


def _check(request: HttpRequest) -> None:
    if not can_transfer_content(request):
        raise PermissionDenied


class ImportForm(forms.Form):
    archive = forms.FileField(
        label=gettext_lazy("Archive"),
        help_text=gettext_lazy("The .zip file exported from the other site."),
        widget=forms.ClearableFileInput(attrs={"accept": ".zip,application/zip"}),
    )
    mode = forms.ChoiceField(
        label=gettext_lazy("Pages and media that already exist here"),
        choices=ImportMode.choices,
        initial=ImportMode.REPLACE,
        widget=forms.RadioSelect,
    )

    def clean_archive(self) -> Any:
        upload = self.cleaned_data["archive"]
        if upload.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(_("The archive is too large."))
        # Checked now, so a wrong file is refused before it is queued.
        try:
            archive, _manifest = open_archive(upload, settings.CONTENT_TRANSFER_KEY)
        except ArchiveError as error:
            raise forms.ValidationError(str(error)) from error
        archive.close()
        upload.seek(0)
        return upload


class ContentTransferView(WagtailAdminTemplateMixin, FormView):
    template_name = "core/admin/content_transfer.html"
    page_title = gettext_lazy("Content transfer")
    header_icon = "download"
    form_class = ImportForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        _check(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        jobs = list(ContentTransfer.objects.select_related("created_by")[:RECENT_JOBS])
        context.update(
            jobs=jobs,
            running=any(not job.is_finished for job in jobs),
            import_enabled=settings.CONTENT_IMPORT_ENABLED,
            signed=bool(settings.CONTENT_TRANSFER_KEY),
            keep_days=settings.CONTENT_TRANSFER_DAYS,
        )
        return context

    def form_valid(self, form: ImportForm) -> HttpResponseRedirect:
        if not settings.CONTENT_IMPORT_ENABLED:
            raise PermissionDenied
        upload = form.cleaned_data["archive"]
        job = ContentTransfer(
            kind=ContentTransferKind.IMPORT,
            mode=form.cleaned_data["mode"],
            original_name=upload.name[:255],
            created_by=cast(User, self.request.user),
        )
        job.archive.save(upload.name, upload, save=False)
        job.save()
        audit(
            job,
            "core.content.import",
            user=self.request.user,
            mode=job.mode,
            file=job.original_name,
        )
        _queue(job)
        messages.success(self.request, _("The import has started."))
        return HttpResponseRedirect(reverse("admin_content_transfer"))


def _queue(job: ContentTransfer) -> None:
    from django.db import transaction

    from core.tasks import run_content_transfer

    transaction.on_commit(lambda: run_content_transfer.delay(job.pk))  # type: ignore[attr-defined]


@require_POST
def start_export(request: HttpRequest) -> HttpResponseRedirect:
    _check(request)
    job = ContentTransfer.objects.create(
        kind=ContentTransferKind.EXPORT, created_by=cast(User, request.user)
    )
    audit(job, "core.content.export", user=request.user)
    _queue(job)
    messages.success(request, _("The export has started."))
    return HttpResponseRedirect(reverse("admin_content_transfer"))


@require_GET
def download_export(request: HttpRequest, pk: int) -> FileResponse:
    _check(request)
    job = ContentTransfer.objects.filter(
        pk=pk, kind=ContentTransferKind.EXPORT, status=ContentTransferStatus.DONE
    ).first()
    if job is None or not job.archive:
        raise Http404
    try:
        handle = job.archive.open("rb")
    except FileNotFoundError as error:
        raise Http404 from error
    audit(job, "core.content.download", user=request.user)
    filename = f"contenu-{job.created_at:%Y%m%d-%H%M}.zip"
    response = FileResponse(handle, as_attachment=True, filename=filename)
    response["Cache-Control"] = "no-store"
    return response
