from typing import Any, TypedDict
import os

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from wagtail.models import Page

from legal.models import (
    TermsOfServicePage,
    PrivacyPolicyPage,
    CookiesPolicyPage,
    CodeOfConductPage,
)


class PageMappingEntry(TypedDict):
    model: type[Page]
    filename: str


class Command(BaseCommand):
    help = "Populates legal pages content from placeholder HTML files."

    PAGE_MAPPING: dict[str, PageMappingEntry] = {
        "terms_of_service": {
            "model": TermsOfServicePage,
            "filename": "terms_of_service.html",
        },
        "privacy_policy": {
            "model": PrivacyPolicyPage,
            "filename": "privacy_policy.html",
        },
        "cookies_policy": {
            "model": CookiesPolicyPage,
            "filename": "cookies_policy.html",
        },
        "code_of_conduct": {
            "model": CodeOfConductPage,
            "filename": "code_of_conduct.html",
        },
    }

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--include",
            nargs="+",
            help="List of pages to include (keys: terms_of_service, privacy_policy, cookies_policy, code_of_conduct)",
        )
        parser.add_argument(
            "--exclude",
            nargs="+",
            help="List of pages to exclude",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        include_list = options["include"]
        exclude_list = options["exclude"] or []

        pages_to_process = list(self.PAGE_MAPPING.keys())

        if include_list:
            pages_to_process = [p for p in pages_to_process if p in include_list]

        pages_to_process = [p for p in pages_to_process if p not in exclude_list]

        if not pages_to_process:
            self.stdout.write(self.style.WARNING("No pages selected to process."))
            return

        base_dir = os.path.join("legal", "templates", "legal", "placeholders")

        for page_key in pages_to_process:
            config = self.PAGE_MAPPING[page_key]
            model_class = config["model"]
            filename = config["filename"]
            file_path = os.path.join(base_dir, filename)

            if not os.path.exists(file_path):
                self.stdout.write(self.style.ERROR(f"Placeholder file not found: {file_path}"))
                continue

            page = model_class.objects.first()
            if not page:
                self.stdout.write(
                    self.style.WARNING(f"Page model instance not found for {page_key}")
                )
                continue

            self.stdout.write(f"Processing {page_key}...")

            old_file_path = file_path + ".old"
            current_html = ""
            if page.content:
                # With RichTextField, content is stored as HTML string
                # RichText object wraps it but often behaves like string or has .source depending on context
                # Wagtail's RichTextField in model instance returns raw HTML string usually
                current_html = str(page.content)

            try:
                with open(old_file_path, "w", encoding="utf-8") as f:
                    f.write(current_html.strip())
                self.stdout.write(f"  Backed up current content to {old_file_path}")
            except IOError as e:
                self.stdout.write(self.style.ERROR(f"  Failed to write backup file: {e}"))
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    new_html = f.read()
            except IOError as e:
                self.stdout.write(
                    self.style.ERROR(f"  Failed to read placeholder file {file_path}: {e}")
                )
                continue

            page.content = new_html

            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"  Updated content for {page_key}"))
