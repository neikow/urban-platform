from typing import Any

from django.core.management.base import BaseCommand

from home.models import HomePage
from publications.models import PublicationIndexPage


class Command(BaseCommand):
    help = "Create the Publications index page if it doesn't exist"

    def handle(self, *args: Any, **options: Any) -> None:
        home = HomePage.objects.first()

        if not home:
            self.stdout.write(self.style.ERROR("HomePage not found. Please create it first."))
            return

        if PublicationIndexPage.objects.exists():
            publication_index = PublicationIndexPage.objects.first()
            self.stdout.write(
                self.style.WARNING(
                    f"PublicationIndexPage already exists: {publication_index.title}"
                )
            )

            # Ensure show_in_menus is True
            if not publication_index.show_in_menus:
                publication_index.show_in_menus = True
                publication_index.save()
                self.stdout.write(self.style.SUCCESS("Enabled show_in_menus for existing page"))
            return

        publication_index = PublicationIndexPage(
            title="Publications",
            slug="publications",
            show_in_menus=True,
            page_introduction="Découvrez les projets et événements en cours et à venir dans votre quartier.",
        )
        home.add_child(instance=publication_index)
        publication_index.save_revision().publish()

        self.stdout.write(
            self.style.SUCCESS(
                f"Created and published PublicationIndexPage: {publication_index.title}"
            )
        )
