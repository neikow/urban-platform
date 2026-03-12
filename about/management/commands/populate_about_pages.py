from typing import Any

from django.core.management.base import BaseCommand

from about.models import AboutWebsitePage, AboutCommissionPage, AboutDevTeamPage


class Command(BaseCommand):
    help = "Populates about pages with placeholder content."

    def handle(self, *args: Any, **options: Any) -> None:
        about_website = AboutWebsitePage.objects.first()
        about_commission = AboutCommissionPage.objects.first()
        about_dev_team = AboutDevTeamPage.objects.first()

        pages = [
            (about_website, "About Website"),
            (about_commission, "About Commission"),
            (about_dev_team, "About Dev Team"),
        ]

        for page, label in pages:
            if not page:
                self.stdout.write(self.style.WARNING(f"Page not found: {label}"))
                continue

            if not page.content:
                page.content = f"<p>Contenu de la page {page.title}.</p>"
                page.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"Updated content for {label}"))
            else:
                self.stdout.write(f"Content already set for {label}, skipping.")
