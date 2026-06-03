"""Import an archive produced by ``export_content``.

    python manage.py import_content content.zip

Media is imported preserving its original primary key (so StreamField and
rich-text references stay valid); pages are upserted by slug under the matching
index page. The whole import runs in a single transaction.
See :mod:`core.management.commands._content_transfer`.
"""

from __future__ import annotations

import json
import zipfile
from typing import Any

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Page

from pedagogy.models.pedagogy_card import PedagogyCardPage
from pedagogy.models.pedagogy_index import PedagogyIndexPage
from pedagogy.models.pedagogy_resource import PedagogyResource
from publications.models.external_link import ProjectExternalLink
from publications.models.project import ProjectPage
from publications.models.publication_index import PublicationIndexPage

from ._content_transfer import (
    ARCHIVE_VERSION,
    HOME_LABEL,
    MANIFEST_NAME,
    deserialize_field,
    sha256_bytes,
)

# Map a parent index ``label_lower`` to its (max_count=1) page model.
_PARENT_MODELS: dict[str, type[Page]] = {
    "publications.publicationindexpage": PublicationIndexPage,
    "pedagogy.pedagogyindexpage": PedagogyIndexPage,
}


class Command(BaseCommand):
    help = "Import publications, pedagogy cards and media from a .zip archive."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archive", type=str, help="Path to the .zip archive to import.")

    def handle(self, *args: Any, **options: Any) -> None:
        archive_path = options["archive"]

        try:
            archive = zipfile.ZipFile(archive_path)
        except (FileNotFoundError, zipfile.BadZipFile) as exc:
            raise CommandError(f"Cannot open archive {archive_path!r}: {exc}") from exc

        with archive:
            manifest = json.loads(archive.read(MANIFEST_NAME))
            version = manifest.get("version")
            if version != ARCHIVE_VERSION:
                raise CommandError(
                    f"Unsupported archive version {version!r} (expected {ARCHIVE_VERSION})."
                )

            with transaction.atomic():
                images = self._import_images(archive, manifest["images"])
                documents = self._import_documents(archive, manifest["documents"])
                pages = self._import_pages(manifest["pages"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {pages['created']} new and {pages['updated']} updated page(s); "
                f"{images} image(s) and {documents} document(s) synced."
            )
        )

    # -- media ---------------------------------------------------------------

    def _import_images(self, archive: zipfile.ZipFile, entries: list[dict[str, Any]]) -> int:
        for entry in entries:
            data = archive.read(entry["file"])
            existing = Image.objects.filter(pk=entry["pk"]).first()

            if existing is None:
                image = Image(pk=entry["pk"], title=entry["title"])
                image.file.save(entry["filename"], ContentFile(data), save=False)
                # Set dimensions after the file (saving the file resets them).
                image.width = entry["width"]
                image.height = entry["height"]
                image.save()
                continue

            existing.title = entry["title"]
            if self._read_hash(existing) != entry["sha256"]:
                existing.file.save(entry["filename"], ContentFile(data), save=False)
                existing.width = entry["width"]
                existing.height = entry["height"]
                existing.renditions.all().delete()
            existing.save()

        return len(entries)

    def _import_documents(self, archive: zipfile.ZipFile, entries: list[dict[str, Any]]) -> int:
        for entry in entries:
            data = archive.read(entry["file"])
            existing = Document.objects.filter(pk=entry["pk"]).first()

            if existing is None:
                document = Document(pk=entry["pk"], title=entry["title"])
                document.file.save(entry["filename"], ContentFile(data), save=False)
                document.save()
                continue

            existing.title = entry["title"]
            if self._read_hash(existing) != entry["sha256"]:
                existing.file.save(entry["filename"], ContentFile(data), save=False)
            existing.save()

        return len(entries)

    @staticmethod
    def _read_hash(obj: Any) -> str | None:
        try:
            obj.file.open("rb")
            try:
                return sha256_bytes(obj.file.read())
            finally:
                obj.file.close()
        except (FileNotFoundError, ValueError, OSError):
            return None

    # -- pages ---------------------------------------------------------------

    def _import_pages(self, entries: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"created": 0, "updated": 0}

        for entry in entries:
            model = apps.get_model(*entry["model"].split("."))

            if entry["model"] == HOME_LABEL:
                # Singleton site root: update the existing instance in place.
                page = self._resolve_home(model)
                self._apply_fields(page, entry, model)
                page.save()
                counts["updated"] += 1
            else:
                parent = self._resolve_parent(entry["parent_model"])
                existing = model.objects.child_of(parent).filter(slug=entry["slug"]).first()

                if existing is None:
                    page = model()
                    self._apply_fields(page, entry, model)
                    page.live = entry["live"]
                    parent.add_child(instance=page)
                    counts["created"] += 1
                else:
                    page = existing
                    self._apply_fields(page, entry, model)
                    page.save()
                    counts["updated"] += 1

            revision = page.save_revision()
            if entry["live"]:
                revision.publish()
            elif page.live:
                page.unpublish()

            self._sync_children(page, entry["children_relations"])

        return counts

    @staticmethod
    def _resolve_home(model: type[Page]) -> Page:
        page = model.objects.first()
        if page is None:
            raise CommandError(
                f"No {model.__name__} exists on this site; create it before importing."
            )
        return page

    @staticmethod
    def _resolve_parent(parent_label: str) -> Page:
        model = _PARENT_MODELS.get(parent_label)
        if model is None:
            raise CommandError(f"Unknown parent model {parent_label!r} in archive.")
        parent = model.objects.first()
        if parent is None:
            raise CommandError(
                f"No {model.__name__} exists on this site; create it before importing."
            )
        return parent

    @staticmethod
    def _apply_fields(page: Any, entry: dict[str, Any], model: type[Page]) -> None:
        page.title = entry["title"]
        page.slug = entry["slug"]
        # HomePage has no hero image; skip the field when the model lacks it.
        if hasattr(page, "hero_image_id"):
            page.hero_image_id = entry["hero_image_pk"]
        for name, value in entry["fields"].items():
            setattr(page, name, deserialize_field(model, name, value))

        stream_block = model._meta.get_field("content").stream_block
        page.content = stream_block.to_python(entry["content"])

    @staticmethod
    def _sync_children(page: Any, relations: dict[str, Any]) -> None:
        if isinstance(page, ProjectPage) and "external_links" in relations:
            page.external_links.all().delete()
            for link in relations["external_links"]:
                ProjectExternalLink.objects.create(
                    page=page,
                    title=link["title"],
                    url=link["url"],
                    tooltip=link["tooltip"],
                    sort_order=link["sort_order"],
                )

        if isinstance(page, PedagogyCardPage) and "resources" in relations:
            page.resources.all().delete()
            for resource in relations["resources"]:
                PedagogyResource.objects.create(
                    page=page,
                    url=resource["url"],
                    document_id=resource["document_pk"],
                    sort_order=resource["sort_order"],
                )
