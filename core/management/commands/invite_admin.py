"""Send the first administrator's invitation again (TENANT_ADMIN_EMAIL).

Asked from the platform's control plane, through its deployment agent, when the first
invitation was lost or expired. Only for that account, and only while it has no
password: an administrator who already chose one resets it from the login page.
"""

import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send the invitation of the first administrator (TENANT_ADMIN_EMAIL) again."

    def handle(self, *args: Any, **options: Any) -> None:
        from core.emails.tasks import send_invitation_email
        from core.models import User

        email = os.environ.get("TENANT_ADMIN_EMAIL", "").strip()
        if not email:
            raise CommandError("TENANT_ADMIN_EMAIL is not set.")
        user = User.objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"No account for {email}: deploy the website again to create it.")
        if user.has_usable_password():
            raise CommandError(
                f"{email} already chose a password: they can reset it from the login page."
            )
        send_invitation_email.delay(user.pk)  # type: ignore[attr-defined]
        self.stdout.write(f"Invitation sent again to {email}.")
