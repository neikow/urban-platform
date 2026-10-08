"""Email new project timeline entries to participants who opted in."""

from functools import partial

from django.db import transaction
from django.utils.translation import gettext as _

from core.models import NotificationDispatch
from core.notifications import NotificationKind
from core.notifications.recipients import opted_in
from core.notifications.tasks import absolute_url, notify
from publications.models import FormResponse, IdeaResponse, ProjectPage, ProjectUpdate


def queue_new_updates(project: ProjectPage) -> None:
    """After a publish, queue an email for each update that was never sent."""
    from publications.tasks import send_project_update

    def queue(update_id: int) -> None:
        send_project_update.delay(update_id)  # type: ignore[attr-defined]

    for update_id in project.updates.filter(notify_participants=True).values_list("pk", flat=True):
        transaction.on_commit(partial(queue, update_id))


def participant_ids(project: ProjectPage) -> set[int]:
    voters = FormResponse.objects.filter(project=project).values_list("user_id", flat=True)
    contributors = IdeaResponse.objects.filter(project=project).values_list("user_id", flat=True)
    return set(voters) | set(contributors)


def send_project_update_now(update: ProjectUpdate) -> int:
    if not NotificationDispatch.claim(NotificationKind.PROJECT_UPDATE, f"update:{update.pk}"):
        return 0

    project = ProjectPage.objects.get(pk=update.page_id)
    if not project.live:
        return 0
    sent = notify(
        NotificationKind.PROJECT_UPDATE,
        opted_in(NotificationKind.PROJECT_UPDATE, participant_ids(project)),
        subject=_("%(project)s: %(title)s") % {"project": project.title, "title": update.title},
        template="emails/notifications/project_update.html",
        context={
            "project_title": project.title,
            "project_url": absolute_url(project.url or "/") + "#suivi",
            "update_title": update.title,
            "update_body": update.body,
            "update_date": update.date.isoformat(),
        },
    )
    from core.audit import audit

    audit(project, "publications.project_update.sent", title=update.title, recipients=sent)
    return sent
