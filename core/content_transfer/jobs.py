"""Exports and imports as background jobs (ContentTransfer, core.tasks)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Callable

from django.conf import settings
from django.core.files.base import File
from django.utils import timezone

from core.models import ContentTransfer, ContentTransferStatus

from .archive import ArchiveError
from .exporter import export_archive
from .importer import import_archive

logger = logging.getLogger(__name__)


def _run(job: ContentTransfer, work: Callable[[ContentTransfer, list[str]], dict]) -> None:
    if job.status != ContentTransferStatus.PENDING:
        return  # already run (a task delivered twice)
    job.status = ContentTransferStatus.RUNNING
    job.save(update_fields=["status"])
    messages: list[str] = []
    try:
        job.summary = work(job, messages)
        job.status = ContentTransferStatus.DONE
    except ArchiveError as error:
        job.error = str(error)
        job.status = ContentTransferStatus.FAILED
    except Exception as error:  # noqa: BLE001 - the job records any failure
        logger.exception("Content transfer %s failed", job.pk)
        job.error = f"{type(error).__name__}: {error}"
        job.status = ContentTransferStatus.FAILED
    job.messages = messages
    job.finished_at = timezone.now()
    job.save()


def run_export(job: ContentTransfer) -> None:
    def work(job: ContentTransfer, messages: list[str]) -> dict:
        import tempfile

        with tempfile.TemporaryFile() as output:
            counts = export_archive(output, key=settings.CONTENT_TRANSFER_KEY, log=messages.append)
            output.seek(0)
            job.archive.save("export.zip", File(output), save=False)
        return counts

    _run(job, work)


def run_import(job: ContentTransfer) -> None:
    def work(job: ContentTransfer, messages: list[str]) -> dict:
        if not settings.CONTENT_IMPORT_ENABLED:
            raise ArchiveError("Importing is disabled on this site.")
        with job.archive.open("rb") as archive:
            return import_archive(
                archive, mode=job.mode, key=settings.CONTENT_TRANSFER_KEY, log=messages.append
            )

    _run(job, work)


def prune_archives() -> int:
    """Delete the archives (and their jobs) older than CONTENT_TRANSFER_DAYS."""
    old = ContentTransfer.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=settings.CONTENT_TRANSFER_DAYS)
    )
    count = 0
    for job in old:
        if job.archive:
            job.archive.delete(save=False)
        job.delete()
        count += 1
    return count
