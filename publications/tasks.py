from celery import shared_task

from publications.models import ProjectPage


@shared_task
def close_expired_polls() -> int:
    from publications.polls import close_expired_polls as close

    return close()


@shared_task
def send_poll_results(project_id: int) -> int:
    from publications.polls import send_poll_results_now

    project = ProjectPage.objects.filter(pk=project_id).first()
    return send_poll_results_now(project) if project else 0


@shared_task
def send_project_update(update_id: int) -> int:
    from publications.models import ProjectUpdate
    from publications.project_updates import send_project_update_now

    update = ProjectUpdate.objects.filter(pk=update_id).first()
    return send_project_update_now(update) if update else 0
