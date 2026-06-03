"""Export publications, pedagogy cards and their media to a portable archive.

    python manage.py export_content --output content.zip

The resulting ``.zip`` can be moved to another environment and loaded with
``import_content``. See :mod:`core.management.commands._content_transfer`.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from wagtail.documents.models import Document
from wagtail.images.models import Image

from home.models import HomePage
from pedagogy.models.pedagogy_card import PedagogyCardPage
from publications.models.event import EventPage
from publications.models.project import ProjectPage

from ._content_transfer import (
    ARCHIVE_VERSION,
    COMMON_PAGE_FIELDS,
    MANIFEST_NAME,
    PAGE_FIELD_SPECS,
    collect_media_ids,
    serialize_field,
    sha256_bytes,
)


class Command(BaseCommand):
    help = "Export publications, pedagogy cards and their media to a .zip archive."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default=None,
            help="Path of the .zip archive to write (default: content-<timestamp>.zip).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        output = options["output"] or self._default_output()
        output_path = Path(output)

        pages: list[dict[str, Any]] = []
        image_ids: set[int] = set()
        document_ids: set[int] = set()

        for page in self._iter_pages():
            entry, page_image_ids, page_document_ids = self._serialize_page(page)
            pages.append(entry)
            image_ids |= page_image_ids
            document_ids |= page_document_ids

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            images: list[dict[str, Any]] = []
            for pk in sorted(image_ids):
                image_entry = self._write_image(archive, pk)
                if image_entry is not None:
                    images.append(image_entry)

            documents: list[dict[str, Any]] = []
            for pk in sorted(document_ids):
                document_entry = self._write_document(archive, pk)
                if document_entry is not None:
                    documents.append(document_entry)

            manifest: dict[str, Any] = {
                "version": ARCHIVE_VERSION,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "images": images,
                "documents": documents,
                "pages": pages,
            }
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, ensure_ascii=False))

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {len(pages)} page(s), {len(images)} image(s) "
                f"and {len(documents)} document(s) to {output_path}"
            )
        )

    @staticmethod
    def _default_output() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"content-{stamp}.zip"

    @staticmethod
    def _iter_pages() -> list[HomePage | ProjectPage | EventPage | PedagogyCardPage]:
        return [
            *HomePage.objects.all(),
            *ProjectPage.objects.all(),
            *EventPage.objects.all(),
            *PedagogyCardPage.objects.all(),
        ]

    def _serialize_page(self, page: Any) -> tuple[dict[str, Any], set[int], set[int]]:
        label = page._meta.label_lower
        parent = page.get_parent()

        raw_content = page.content.get_prep_value()
        image_ids, document_ids = collect_media_ids(raw_content)
        # HomePage has no hero image; other transferred pages do.
        hero_image_id = getattr(page, "hero_image_id", None)
        if hero_image_id:
            image_ids.add(hero_image_id)

        entry: dict[str, Any] = {
            "model": label,
            "parent_model": parent.specific_class._meta.label_lower if parent else None,
            "slug": page.slug,
            "title": page.title,
            "live": page.live,
            "hero_image_pk": hero_image_id,
            "content": raw_content,
            "fields": {
                name: serialize_field(page, name)
                for name in COMMON_PAGE_FIELDS + PAGE_FIELD_SPECS.get(label, [])
            },
            "children_relations": {},
        }

        if isinstance(page, ProjectPage):
            entry["children_relations"]["external_links"] = [
                {
                    "title": link.title,
                    "url": link.url,
                    "tooltip": link.tooltip,
                    "sort_order": link.sort_order,
                }
                for link in page.external_links.all()
            ]
        if isinstance(page, PedagogyCardPage):
            resources = []
            for resource in page.resources.all():
                resources.append(
                    {
                        "url": resource.url,
                        "document_pk": resource.document_id,
                        "sort_order": resource.sort_order,
                    }
                )
                if resource.document_id:
                    document_ids.add(resource.document_id)
            entry["children_relations"]["resources"] = resources

        return entry, image_ids, document_ids

    def _write_image(self, archive: zipfile.ZipFile, pk: int) -> dict[str, Any] | None:
        image = Image.objects.filter(pk=pk).first()
        if image is None:
            self.stdout.write(self.style.WARNING(f"Skipping missing image pk={pk}"))
            return None

        data = self._read_file(image)
        if data is None:
            self.stdout.write(self.style.WARNING(f"Skipping image pk={pk} (file unreadable)"))
            return None

        filename = Path(image.file.name).name
        arcname = f"media/images/{pk}__{filename}"
        archive.writestr(arcname, data)
        return {
            "pk": pk,
            "title": image.title,
            "file": arcname,
            "filename": filename,
            "sha256": sha256_bytes(data),
            "width": image.width,
            "height": image.height,
        }

    def _write_document(self, archive: zipfile.ZipFile, pk: int) -> dict[str, Any] | None:
        document = Document.objects.filter(pk=pk).first()
        if document is None:
            self.stdout.write(self.style.WARNING(f"Skipping missing document pk={pk}"))
            return None

        data = self._read_file(document)
        if data is None:
            self.stdout.write(self.style.WARNING(f"Skipping document pk={pk} (file unreadable)"))
            return None

        filename = Path(document.file.name).name
        arcname = f"media/documents/{pk}__{filename}"
        archive.writestr(arcname, data)
        return {
            "pk": pk,
            "title": document.title,
            "file": arcname,
            "filename": filename,
            "sha256": sha256_bytes(data),
        }

    @staticmethod
    def _read_file(obj: Any) -> bytes | None:
        try:
            obj.file.open("rb")
            try:
                return obj.file.read()
            finally:
                obj.file.close()
        except (FileNotFoundError, ValueError, OSError):
            return None
