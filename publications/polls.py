"""Closing polls and sending their results."""

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import NotificationDispatch, User
from core.notifications import NotificationKind
from core.notifications.recipients import opted_in
from core.notifications.tasks import absolute_url, notify
from publications.models import (
    FormResponse,
    ParticipationMode,
    PollClosure,
    PollClosureReason,
    ProjectPage,
)


def close_poll(
    project: ProjectPage, reason: PollClosureReason, closed_by: User | None = None
) -> PollClosure:
    """Close the poll (idempotent) and queue the results email once committed."""
    closure, created = PollClosure.objects.get_or_create(
        project=project, defaults={"reason": reason, "closed_by": closed_by}
    )
    if created:
        from core.audit import audit

        audit(project, "publications.poll.close", user=closed_by, reason=str(reason))
    from publications.tasks import send_poll_results

    transaction.on_commit(lambda: send_poll_results.delay(project.pk))  # type: ignore[attr-defined]
    return closure


def close_expired_polls() -> int:
    """Close polls whose end date has passed. Returns how many were closed."""
    expired = (
        ProjectPage.objects.live()
        .filter(
            participation_mode=ParticipationMode.VOTING,
            voting_end_date__lte=timezone.now(),
            poll_closure__isnull=True,
        )
        .specific()
    )
    count = 0
    for project in expired:
        close_poll(project, PollClosureReason.END_DATE)
        count += 1
    return count


def send_poll_results_now(project: ProjectPage) -> int:
    """Email the final results to voters who opted in, once per project."""
    from publications.services import get_final_vote_results

    if not NotificationDispatch.claim(NotificationKind.POLL_RESULTS, f"project:{project.pk}"):
        return 0

    results = get_final_vote_results(project)
    voter_ids = FormResponse.objects.filter(project=project).values_list("user_id", flat=True)
    context = {
        "project_title": project.title,
        "project_url": absolute_url(project.url or "/"),
        "question": project.vote_question,
        "total_votes": results["total_votes"],
        "rows": [
            {"label": str(row["label"]), "count": row["count"], "percentage": row["percentage"]}
            for row in results["ordered"]
        ],
    }
    sent = notify(
        NotificationKind.POLL_RESULTS,
        opted_in(NotificationKind.POLL_RESULTS, voter_ids),
        subject=_("Poll results: %(title)s") % {"title": project.title},
        template="emails/notifications/poll_results.html",
        context=context,
    )
    from core.audit import audit

    audit(project, "publications.poll.results_sent", recipients=sent)
    return sent
