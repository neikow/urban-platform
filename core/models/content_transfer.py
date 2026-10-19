import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _


class TransferStorage(FileSystemStorage):
    """Archives live under MEDIA_ROOT/transfers/, which nginx refuses to serve.

    They are only handed out by the download view, to superusers. No base URL:
    nothing builds a public link to them. The folder follows MEDIA_ROOT (read
    on each use, not when the model is loaded).
    """

    def __init__(self) -> None:
        super().__init__(base_url=None)

    @property  # type: ignore[override]
    def base_location(self) -> str:
        return str(Path(settings.MEDIA_ROOT) / "transfers")

    @property  # type: ignore[override]
    def location(self) -> str:
        return str(Path(self.base_location).resolve())


def transfer_storage() -> FileSystemStorage:
    return TransferStorage()


def archive_name(instance: Any, filename: str) -> str:
    return f"{instance.kind}-{uuid.uuid4().hex}.zip"


class ContentTransferKind(models.TextChoices):
    EXPORT = "export", _("Export")
    IMPORT = "import", _("Import")


class ContentTransferStatus(models.TextChoices):
    PENDING = "pending", _("Waiting")
    RUNNING = "running", _("Running")
    DONE = "done", _("Done")
    FAILED = "failed", _("Failed")


class ContentTransfer(models.Model):
    """An export or an import of content (core.content_transfer), run as a background job."""

    kind = models.CharField(_("Kind"), max_length=10, choices=ContentTransferKind.choices)
    mode = models.CharField(_("Mode"), max_length=10, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=ContentTransferStatus.choices,
        default=ContentTransferStatus.PENDING,
    )
    archive = models.FileField(
        _("Archive"), storage=transfer_storage, upload_to=archive_name, blank=True
    )
    original_name = models.CharField(_("File name"), max_length=255, blank=True)
    summary = models.JSONField(_("Summary"), default=dict, blank=True)
    messages = models.JSONField(_("Messages"), default=list, blank=True)
    error = models.TextField(_("Error"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Started by"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    created_at = models.DateTimeField(_("Started on"), auto_now_add=True)
    finished_at = models.DateTimeField(_("Finished on"), null=True, blank=True)

    class Meta:
        verbose_name = _("Content transfer")
        verbose_name_plural = _("Content transfers")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_finished(self) -> bool:
        return self.status in (ContentTransferStatus.DONE, ContentTransferStatus.FAILED)
