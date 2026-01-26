from typing import Any

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.conf import settings

from publications.models import PublicationIndexPage
from publications.factories import ProjectPageFactory, EventPageFactory


class Command(BaseCommand):
    help = "Create mock publications (projects and events). Only works in DEBUG mode."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--projects",
            type=int,
            default=5,
            help="Number of projects to create (default: 5)",
        )
        parser.add_argument(
            "--events",
            type=int,
            default=5,
            help="Number of events to create (default: 5)",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all existing publications before creating new ones",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            self.stderr.write(self.style.ERROR("This command can only be run when DEBUG=True"))
            return

        index_page = PublicationIndexPage.objects.first()

        if not index_page:
            self.stderr.write(
                self.style.ERROR(
                    "No PublicationIndexPage found. Please run 'python manage.py create_project_index' first."
                )
            )
            return

        if options["delete"]:
            children = index_page.get_children().specific()
            deleted_count = 0
            for child in children:
                child.delete()
                deleted_count += 1
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} existing publications."))

        projects_count = options["projects"]
        events_count = options["events"]

        # Create projects
        self.stdout.write(f"Creating {projects_count} projects...")
        for i in range(projects_count):
            try:
                page = ProjectPageFactory.create(parent=index_page)
                page.save_revision().publish()
                self.stdout.write(f"  Created project: {page.title}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Failed to create project {i + 1}: {e}"))

        # Create events
        self.stdout.write(f"Creating {events_count} events...")
        for i in range(events_count):
            try:
                page = EventPageFactory.create(parent=index_page)
                page.save_revision().publish()
                self.stdout.write(f"  Created event: {page.title}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Failed to create event {i + 1}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {projects_count} projects and {events_count} events."
            )
        )
