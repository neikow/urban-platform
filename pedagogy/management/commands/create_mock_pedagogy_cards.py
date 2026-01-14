from django.core.management.base import BaseCommand
from django.conf import settings
from pedagogy.models import PedagogyIndexPage
from pedagogy.factories import PedagogyCardPageFactory
from home.models import HomePage


class Command(BaseCommand):
    help = "Create mock pedagogy cards. Only works in DEBUG mode."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=10, help="Number of cards to create"
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR("This command can only be run when DEBUG=True")
            )
            return

        count = options["count"]

        # Find or create Pedagogy Index Page
        index_page = PedagogyIndexPage.objects.first()
        if not index_page:
            self.stdout.write(
                "PedagogyIndexPage not found. Attempting to create one..."
            )
            # We assume a HomePage exists as the parent
            home = HomePage.objects.first()
            if not home:
                self.stderr.write(
                    self.style.ERROR(
                        "No HomePage found. Cannot create PedagogyIndexPage."
                    )
                )
                return

            index_page = PedagogyIndexPage(
                title="Fiches pédagogiques", slug="fiches-pedagogiques"
            )
            # add_child saves the instance
            home.add_child(instance=index_page)
            # Publish the index page too
            index_page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(f"Created PedagogyIndexPage: {index_page.title}")
            )
        else:
            self.stdout.write(f"Using existing PedagogyIndexPage: {index_page.title}")

        self.stdout.write(
            f"Creating {count} mock pedagogy entries under '{index_page.title}'..."
        )

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
