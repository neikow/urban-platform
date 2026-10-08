from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.conf import settings
from django.template.loader import render_to_string

from sib_api_v3_sdk.rest import ApiException  # type: ignore[import-untyped]

from core.branding import site_name, sender_name

if TYPE_CHECKING:
    from core.models import User


class FailedToSendEmail(Exception):
    pass


class EmailService(ABC):
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        headers: dict[str, str] | None = None,
    ) -> bool:
        pass

    def send_verification_email(self, user: "User", verification_url: str) -> bool:
        html_content = render_to_string(
            "emails/verification_email.html",
            {
                "user": user,
                "verification_url": verification_url,
                "site_name": site_name(),
            },
        )
        return self.send_email(
            to_email=user.email,
            to_name=user.get_full_name(),
            subject=f"Confirmez votre adresse email - {site_name()}",
            html_content=html_content,
        )

    def send_password_reset_email(self, user: "User", reset_url: str) -> bool:
        html_content = render_to_string(
            "emails/password_reset_email.html",
            {
                "user": user,
                "reset_url": reset_url,
                "site_name": site_name(),
                "expiry_hours": settings.PASSWORD_RESET_TOKEN_EXPIRY // 3600,
            },
        )
        return self.send_email(
            to_email=user.email,
            to_name=user.get_full_name(),
            subject=f"Réinitialisation de votre mot de passe - {site_name()}",
            html_content=html_content,
        )

    def send_invitation_email(self, user: "User", invitation_url: str) -> bool:
        html_content = render_to_string(
            "emails/invitation_email.html",
            {
                "user": user,
                "reset_url": invitation_url,
                "site_name": site_name(),
                "expiry_days": settings.INVITATION_TOKEN_EXPIRY // 86400,
            },
        )
        return self.send_email(
            to_email=user.email,
            to_name=user.get_full_name(),
            subject=f"Votre accès à {site_name()}",
            html_content=html_content,
        )


class ConsoleEmailService(EmailService):
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        headers: dict[str, str] | None = None,
    ) -> bool:
        print("=" * 60)
        print("EMAIL SENT")
        print("=" * 60)
        print(f"To: {to_name} <{to_email}>")
        print(f"From: {sender_name()} <{settings.DEFAULT_FROM_EMAIL}>")
        print(f"Subject: {subject}")
        for name, value in (headers or {}).items():
            print(f"{name}: {value}")
        print("-" * 60)
        print(html_content)
        print("=" * 60)
        return True


class BrevoEmailService(EmailService):
    def __init__(self) -> None:
        import sib_api_v3_sdk  # type: ignore[import-untyped]

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        headers: dict[str, str] | None = None,
    ) -> bool:
        import sib_api_v3_sdk

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": to_name}],
            sender={"email": settings.DEFAULT_FROM_EMAIL, "name": sender_name()},
            subject=subject,
            html_content=html_content,
            headers=headers or None,
        )

        try:
            self.api_instance.send_transac_email(send_smtp_email)
            return True
        except ApiException as e:
            raise FailedToSendEmail(f"Failed to send email via Brevo: {e}")


def get_email_service() -> EmailService:
    backend = getattr(settings, "EMAIL_SERVICE_BACKEND", "console")
    if backend == "brevo":
        return BrevoEmailService()
    return ConsoleEmailService()
