from datetime import timedelta

from celery import shared_task, Task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import EmailEvent, EmailEventStatus, EmailEventType
from .services import get_email_service, FailedToSendEmail
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

    token = generate_password_reset_token(user)
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
    except FailedToSendEmail as e:
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

    count = old_events.update(
        user=None,
        recipient_email="",
    )

    return count


# Emails about the membership, by kind: their subject. Always sent: they are
# about something the member paid for.
MEMBERSHIP_EMAIL_SUBJECTS = {
    "confirmation": "Votre adhésion est enregistrée",
}


@shared_task(bind=True, max_retries=3)
def send_membership_email(self: Task, user_id: int, kind: str, context: dict) -> bool:
    """Send one email about the user's membership (emails/membership/<kind>.html)."""
    from django.template.loader import render_to_string
    from django.urls import reverse

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return False
    base_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "http://localhost:8000").rstrip("/")
    subject = f"{MEMBERSHIP_EMAIL_SUBJECTS[kind]} - {settings.WEBSITE_NAME}"
    html = render_to_string(
        f"emails/membership/{kind}.html",
        {
            **context,
            "user": user,
            "subject": subject,
            "site_name": settings.WEBSITE_NAME,
            "site_url": f"{base_url}/",
            "membership_url": f"{base_url}{reverse('membership')}",
        },
    )
    event = EmailEvent.objects.create(
        user=user,
        event_type=EmailEventType.MEMBERSHIP,
        status=EmailEventStatus.PENDING,
        recipient_email=user.email,
    )
    try:
        sent = get_email_service().send_email(
            to_email=user.email, to_name=user.get_full_name(), subject=subject, html_content=html
        )
    except FailedToSendEmail as error:
        event.status = EmailEventStatus.FAILED
        event.error_message = str(error)
        event.save()
        raise self.retry(exc=error, countdown=60)
    event.status = EmailEventStatus.SENT if sent else EmailEventStatus.FAILED
    event.sent_at = timezone.now() if sent else None
    event.save()
    return sent
