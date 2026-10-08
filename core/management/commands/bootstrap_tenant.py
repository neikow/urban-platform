"""Bring this website's database in line with its environment (see core.tenant).

Run after `migrate` at every deployment. Exits with an error only when a
step cannot run at all; what can be retried (e.g. the territory service being
down) is reported as a warning, and the next run tries again.
"""

import os
from typing import Any

from django.core.management.base import BaseCommand

from core.tenant import TenantConfig, bootstrap


class Command(BaseCommand):
    help = "Set up this website from its environment: site URL, admin, territory, starter pages."

    def handle(self, *args: Any, **options: Any) -> None:
        report = bootstrap(TenantConfig.from_environment(dict(os.environ)))
        for line in report.done:
            self.stdout.write(self.style.SUCCESS(line))
        for line in report.warnings:
            self.stderr.write(self.style.WARNING(line))
        if not report.done and not report.warnings:
            self.stdout.write("Nothing to do.")
