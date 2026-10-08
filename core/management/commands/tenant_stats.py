"""This website's figures, as JSON, for the platform's deployment agent.

The agent runs it now and then in the ``web`` container and reports the figures to
the control plane (agent/README.md). Nothing personal: counts only.
"""

import json
from typing import Any

from django.core.management.base import BaseCommand
from wagtail.models import Page


def collect() -> dict[str, int]:
    from core.models import User

    return {
        # Published pages, the home page included (not Wagtail's root).
        "pages": Page.objects.live().filter(depth__gt=1).count(),
        # Accounts not deleted and not deactivated.
        "users": User.objects.filter(is_active=True).count(),
    }


class Command(BaseCommand):
    help = "Print this website's figures as JSON: published pages, user accounts."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(json.dumps(collect()))
