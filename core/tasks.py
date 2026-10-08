from celery import shared_task


@shared_task
def reassign_residents() -> int:
    """Attach every located user to the association whose area contains them."""
    from core.associations import reassign_residents as reassign

    return reassign()
