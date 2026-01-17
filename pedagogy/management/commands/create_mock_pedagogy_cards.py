from typing import Any

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.conf import settings
from pedagogy.models import PedagogyIndexPage
from pedagogy.factories import PedagogyCardPageFactory
from home.models import HomePage


class Command(BaseCommand):
    help = "Create mock pedagogy cards. Only works in DEBUG mode."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--count", type=int, default=10, help="Number of cards to create"
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all existing pedagogy cards before creating new ones",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR("This command can only be run when DEBUG=True")
            )
            return

        if options["delete"]:
            index_page = PedagogyIndexPage.objects.first()
            if index_page:
                children = index_page.get_children().specific()
                for child in children:
                    child.delete()
                self.stdout.write(
                    self.style.SUCCESS("Deleted all existing pedagogy cards.")
                )
            else:
                self.stderr.write(
                    self.style.ERROR(
                        "No PedagogyIndexPage found. Please run the migration to create it first."
                    )
                )
                return

        count = options["count"]

        index_page = PedagogyIndexPage.objects.first()

        if not index_page:
            self.stderr.write(
                self.style.ERROR(
                    "No PedagogyIndexPage found. Please run the migration to create it first."
                )
            )
            return

        for i in range(count):
            try:
                page = PedagogyCardPageFactory.create(parent=index_page)
                page.save_revision().publish()
                self.stdout.write(f"Created: {page.title}")
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Failed to create entry {i + 1}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {count} pedagogy entries.")
        )
