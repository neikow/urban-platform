from datetime import timedelta

from celery import shared_task, Task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import EmailEvent, EmailEventStatus, EmailEventType
from .services import get_email_service, FailedToSendEmail
from .tokens import (
    generate_invitation_token,
    generate_password_reset_token,
    generate_verification_token,
)

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_verification_email(self: Task, user_id: int) -> bool:
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return False

    event = EmailEvent.objects.create(
        user=user,
        event_type=EmailEventType.VERIFICATION,
        status=EmailEventStatus.PENDING,
        recipient_email=user.email,
    )

    token = generate_verification_token(user.uuid)
    base_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "http://localhost:8000")
    verification_url = f"{base_url}/auth/verify-email/{token}/"

    email_service = get_email_service()
    try:
        success = email_service.send_verification_email(user, verification_url)
        if success:
            event.status = EmailEventStatus.SENT
            event.sent_at = timezone.now()
        else:
            event.status = EmailEventStatus.FAILED
            event.error_message = "Email service returned failure"
        event.save()
        return success
    except FailedToSendEmail as e:
        event.status = EmailEventStatus.FAILED
        event.error_message = str(e)
        event.save()
        raise self.retry(exc=e, countdown=60)


def _send_password_link(task: Task, user_id: int, invitation: bool) -> bool:
    """A link to choose a password: a reset asked by the user, or an invitation."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return False

    event = EmailEvent.objects.create(
        user=user,
        event_type=EmailEventType.INVITATION if invitation else EmailEventType.PASSWORD_RESET,
        status=EmailEventStatus.PENDING,
        recipient_email=user.email,
    )

    token = generate_invitation_token(user) if invitation else generate_password_reset_token(user)
    base_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "http://localhost:8000")
    url = f"{base_url}/auth/password-reset/{token}/"

    email_service = get_email_service()

    try:
        if invitation:
            success = email_service.send_invitation_email(user, url)
        else:
            success = email_service.send_password_reset_email(user, url)
        if success:
            event.status = EmailEventStatus.SENT
            event.sent_at = timezone.now()
        else:
            event.status = EmailEventStatus.FAILED
            event.error_message = "Email service returned failure"
        event.save()
        return success
    except FailedToSendEmail as e:
        event.status = EmailEventStatus.FAILED
        event.error_message = str(e)
        event.save()
        raise task.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self: Task, user_id: int) -> bool:
    return _send_password_link(self, user_id, invitation=False)


@shared_task(bind=True, max_retries=3)
def send_invitation_email(self: Task, user_id: int) -> bool:
    """Invite an administrator created without a password (core.tenant) to choose one."""
    return _send_password_link(self, user_id, invitation=True)


@shared_task
def anonymize_old_email_events() -> int:
    days = getattr(settings, "EMAIL_EVENT_ANONYMIZE_DAYS", 30)
    cutoff_date = timezone.now() - timedelta(days=days)

    old_events = EmailEvent.objects.filter(
        created_at__lt=cutoff_date,
        user__isnull=False,
    )

    count = old_events.update(
        user=None,
        recipient_email="",
    )

    return count
