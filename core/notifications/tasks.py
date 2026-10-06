from typing import Any

from celery import Task, shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from core.emails.services import FailedToSendEmail, get_email_service
from core.models import EmailEvent, EmailEventStatus, User
from core.notifications import NotificationKind
from core.notifications.tokens import make_unsubscribe_token


def absolute_url(path: str) -> str:
    return f"{settings.WAGTAILADMIN_BASE_URL.rstrip('/')}{path}"


@shared_task(bind=True, max_retries=3)
def send_notification_email(
    self: Task,
    user_id: int,
    kind: str,
    subject: str,
    template: str,
    context: dict[str, Any],
) -> bool:
    """Render and send one notification email, if the user still wants it."""
    notification = NotificationKind(kind)
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None or not getattr(user, notification.preference_field):
        return False

    unsubscribe_url = absolute_url(
        reverse(
            "notification_unsubscribe", args=[make_unsubscribe_token(str(user.uuid), notification)]
        )
    )
    html = render_to_string(
        template,
        {
            **context,
            "user": user,
            "subject": subject,
            "site_name": settings.WEBSITE_NAME,
            "site_url": absolute_url("/"),
            "preferences_url": absolute_url(reverse("profile_edit") + "#notifications"),
            "unsubscribe_url": unsubscribe_url,
            "notification_label": notification.label,
        },
    )

    event = EmailEvent.objects.create(
        user=user,
        event_type=notification.email_event_type,
        status=EmailEventStatus.PENDING,
        recipient_email=user.email,
    )
    try:
        sent = get_email_service().send_email(
            to_email=user.email,
            to_name=user.get_full_name(),
            subject=subject,
            html_content=html,
            # RFC 8058 one-click unsubscribe, shown by Gmail and Apple Mail.
            headers={
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
    except FailedToSendEmail as error:
        event.status = EmailEventStatus.FAILED
        event.error_message = str(error)
        event.save()
        raise self.retry(exc=error, countdown=60)

    event.status = EmailEventStatus.SENT if sent else EmailEventStatus.FAILED
    event.sent_at = timezone.now() if sent else None
    if not sent:
        event.error_message = "Email service returned failure"
    event.save()
    return sent


def notify(
    kind: NotificationKind,
    users: Any,
    subject: str,
    template: str,
    context: dict[str, Any],
) -> int:
    """Queue one email per user; `context` must be JSON-serialisable."""
    count = 0
    for user_id in users.values_list("pk", flat=True):
        send_notification_email.delay(user_id, kind.value, subject, template, context)  # type: ignore[attr-defined]
        count += 1
    return count
