from celery import shared_task


@shared_task
def reassign_residents() -> int:
    """Attach every located user who did not choose to the association of their address."""
    from core.associations import reassign_residents as reassign

    return reassign()


@shared_task
def prune_task_runs() -> int:
    """Forget task runs older than the retention period (admin tasks page)."""
    from core.task_monitor import prune_runs

    return prune_runs()


@shared_task
def prune_security_events() -> int:
    """Forget logins and other security events after a year (activity log)."""
    from core.audit import prune_security_events as prune

    return prune()


@shared_task
def check_membership_payments() -> int:
    """Record the memberships paid on HelloAsso whose notification was lost."""
    from core.membership_payments import check_pending_payments

    return check_pending_payments()


@shared_task
def send_membership_reminders() -> int:
    """Remind members who did not renew, before and after their membership ends."""
    from core.membership_reminders import send_membership_reminders as send

    return send()


@shared_task
def run_content_transfer(job_id: int) -> None:
    """Run an export or an import of content (Settings › Content transfer)."""
    from core.content_transfer.jobs import run_export, run_import
    from core.models import ContentTransfer, ContentTransferKind

    job = ContentTransfer.objects.filter(pk=job_id).first()
    if job is None:
        return
    (run_export if job.kind == ContentTransferKind.EXPORT else run_import)(job)


@shared_task
def prune_content_transfers() -> int:
    """Delete the content archives older than a week."""
    from core.content_transfer.jobs import prune_archives

    return prune_archives()
