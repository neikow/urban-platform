from django.db import models
from django.utils.translation import gettext_lazy as _


class TaskRunStatus(models.TextChoices):
    STARTED = "STARTED", _("Running")
    SUCCESS = "SUCCESS", _("Succeeded")
    FAILURE = "FAILURE", _("Failed")
    RETRY = "RETRY", _("Retrying")


class TaskRun(models.Model):
    """One run of a Celery task, for the admin tasks page (core.task_monitor).

    Written by Celery signals; runs older than RETENTION_DAYS are deleted daily.
    """

    task_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(_("Task"), max_length=255, db_index=True)
    arguments = models.CharField(_("Arguments"), max_length=255, blank=True)
    status = models.CharField(
        _("Status"), max_length=10, choices=TaskRunStatus.choices, default=TaskRunStatus.STARTED
    )
    worker = models.CharField(_("Worker"), max_length=255, blank=True)
    started_at = models.DateTimeField(_("Started"), db_index=True)
    finished_at = models.DateTimeField(_("Finished"), null=True, blank=True)
    result = models.CharField(_("Result"), max_length=255, blank=True)
    error = models.TextField(_("Error"), blank=True)

    class Meta:
        verbose_name = _("Task run")
        verbose_name_plural = _("Task runs")
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.task_id})"

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()
