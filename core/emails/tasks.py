from datetime import timedelta

from celery import shared_task, Task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import EmailEvent, EmailEventStatus, EmailEventType
from .services import get_email_service
from .tokens import generate_verification_token, generate_password_reset_token

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

    token = generate_verification_token(user_id)
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
    except Exception as e:
        event.status = EmailEventStatus.FAILED
        event.error_message = str(e)
        event.save()
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self: Task, user_id: int) -> bool:
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return False

    event = EmailEvent.objects.create(
        user=user,
        event_type=EmailEventType.PASSWORD_RESET,
        status=EmailEventStatus.PENDING,
        recipient_email=user.email,
    )

    token = generate_password_reset_token(user_id)
    base_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "http://localhost:8000")
    reset_url = f"{base_url}/auth/password-reset/{token}/"

    email_service = get_email_service()

    try:
        success = email_service.send_password_reset_email(user, reset_url)
        if success:
            event.status = EmailEventStatus.SENT
            event.sent_at = timezone.now()
        else:
            event.status = EmailEventStatus.FAILED
            event.error_message = "Email service returned failure"
        event.save()
        return success
    except Exception as e:
        event.status = EmailEventStatus.FAILED
        event.error_message = str(e)
        event.save()
        raise self.retry(exc=e, countdown=60)


@shared_task
def anonymize_old_email_events() -> int:
    days = getattr(settings, "EMAIL_EVENT_ANONYMIZE_DAYS", 30)
    cutoff_date = timezone.now() - timedelta(days=days)

    old_events = EmailEvent.objects.filter(
        created_at__lt=cutoff_date,
        user__isnull=False,
    )

    count = old_events.count()

    for event in old_events:
        event.anonymize()

    return count
