from celery import shared_task


@shared_task
def reassign_residents() -> int:
    """Attach every located user to the association whose area contains them."""
    from core.associations import reassign_residents as reassign

    return reassign()


@shared_task
def prune_task_runs() -> int:
    """Forget task runs older than the retention period (admin tasks page)."""
    from core.task_monitor import prune_runs

    return prune_runs()
