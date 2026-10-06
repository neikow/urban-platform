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
