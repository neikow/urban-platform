"""Django email backend sending through the site's email service (Brevo in production).

The site's own emails call the service directly (core.emails.services). This
backend carries the emails Django and Wagtail send themselves, notably the
moderation workflow: a page submitted by an editor, then approved or rejected.
"""

import logging
from collections.abc import Sequence

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import escape, linebreaks

from core.emails.services import get_email_service

logger = logging.getLogger(__name__)


def _html(message: EmailMessage) -> str:
    if isinstance(message, EmailMultiAlternatives):
        for content, mimetype in message.alternatives:
            if mimetype == "text/html":
                return str(content)
    if message.content_subtype == "html":
        return str(message.body)
    return linebreaks(escape(message.body))


class EmailServiceBackend(BaseEmailBackend):
    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        service = get_email_service()
        sent = 0
        for message in email_messages:
            html = _html(message)
            for recipient in [*message.to, *message.cc, *message.bcc]:
                try:
                    if service.send_email(
                        to_email=recipient,
                        to_name="",
                        subject=str(message.subject),
                        html_content=html,
                    ):
                        sent += 1
                except Exception:
                    if not self.fail_silently:
                        raise
                    logger.exception("Could not send %r to %s", message.subject, recipient)
        return sent
