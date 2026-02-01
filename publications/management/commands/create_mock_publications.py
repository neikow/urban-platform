import random
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.utils import timezone

from publications.factories import EventPageFactory, ProjectPageFactory
from publications.models import PublicationIndexPage


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
        parser.add_argument(
            "--with-voting",
            action="store_true",
            default=True,
            help="Enable voting on projects (default: True)",
        )
        parser.add_argument(
            "--no-voting",
            action="store_true",
            help="Disable voting on projects",
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
        enable_voting = options["with_voting"] and not options["no_voting"]

        # Create projects
        self.stdout.write(f"Creating {projects_count} projects...")
        for i in range(projects_count):
            try:
                voting_end_date = None
                if enable_voting and random.random() > 0.3:  # nosec B311
                    voting_end_date = timezone.now() + timedelta(days=random.randint(30, 180))  # nosec B311

                page = ProjectPageFactory.create(
                    parent=index_page,
                    enable_voting=enable_voting,
                    voting_end_date=voting_end_date,
                )
                page.save_revision().publish()

                voting_info = ""
                if enable_voting:
                    if voting_end_date:
                        voting_info = (
                            f" (voting enabled until {voting_end_date.strftime('%Y-%m-%d')})"
                        )
                    else:
                        voting_info = " (voting enabled, no end date)"
                else:
                    voting_info = " (voting disabled)"

                self.stdout.write(f"  Created project: {page.title}{voting_info}")
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
