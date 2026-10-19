"""Load a content archive, replacing what exists or creating new pages beside it."""

from __future__ import annotations

import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.color import no_style
from django.db import connection, models, transaction
from django.utils.translation import gettext_lazy as _
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Page

from pedagogy.models.pedagogy_card import PedagogyCardPage
from pedagogy.models.pedagogy_index import PedagogyIndexPage
from pedagogy.models.pedagogy_resource import PedagogyResource
from publications.models.external_link import ProjectExternalLink
from publications.models.project import ProjectPage
from publications.models.publication_index import PublicationIndexPage

from .archive import (
    HOME_LABEL,
    ArchiveError,
    deserialize_field,
    open_archive,
    read_member,
    remap_media_ids,
    sha256_bytes,
)


class ImportMode(models.TextChoices):
    REPLACE = "replace", _("Replace the existing pages and media")
    CREATE = "create", _("Create new pages, change nothing that exists")


_PARENT_MODELS: dict[str, type[Page]] = {
    "publications.publicationindexpage": PublicationIndexPage,
    "pedagogy.pedagogyindexpage": PedagogyIndexPage,
}

Log = Callable[[str], None]


def import_archive(
    path: str | Path | IO[bytes], mode: str = ImportMode.REPLACE, key: str = "", log: Log = print
) -> dict[str, int]:
    """Import the archive at ``path`` in one transaction. Raises ArchiveError.

    ``replace``: media keep their ids and are updated; pages with the same slug
    under the same index page are updated, the home page too.
    ``create``: nothing that exists changes. A media id taken by another file
    gets a new media (references follow); every page is created, with a free
    slug; the home page, one per site, is left as it is.
    """
    archive, manifest = open_archive(path, key)
    with archive:
        importer = _Importer(archive, ImportMode(mode), log)
        with transaction.atomic():
            importer.import_media(manifest["images"], manifest["documents"])
            importer.import_pages(manifest["pages"])
            _reset_media_sequences()
    return importer.counts


class _Importer:
    def __init__(self, archive: zipfile.ZipFile, mode: ImportMode, log: Log) -> None:
        self.archive = archive
        self.mode = mode
        self.log = log
        self.images: dict[int, int] = {}
        self.documents: dict[int, int] = {}
        self.counts = {
            "pages_created": 0,
            "pages_updated": 0,
            "pages_skipped": 0,
            "media_created": 0,
            "media_updated": 0,
            "media_kept": 0,
        }

    # -- media -----------------------------------------------------------------

    def import_media(self, images: list[dict[str, Any]], documents: list[dict[str, Any]]) -> None:
        for entry in images:
            self.images[entry["pk"]] = self._import_one(Image, entry)
        for entry in documents:
            self.documents[entry["pk"]] = self._import_one(Document, entry)

    def _import_one(self, model: type[Image] | type[Document], entry: dict[str, Any]) -> int:
        data = read_member(self.archive, entry)
        existing = model.objects.filter(pk=entry["pk"]).first()
        same_file = existing is not None and _file_hash(existing) == entry["sha256"]

        if self.mode == ImportMode.CREATE:
            if same_file:
                self.counts["media_kept"] += 1
                return existing.pk  # type: ignore[union-attr]
            # A free id is kept (references stay as they are), a taken one is not.
            media = model(pk=None if existing else entry["pk"], title=entry["title"])
            self._save_file(media, entry, data)
            self.counts["media_created"] += 1
            return media.pk

        if existing is None:
            media = model(pk=entry["pk"], title=entry["title"])
            self._save_file(media, entry, data)
            self.counts["media_created"] += 1
            return media.pk
        existing.title = entry["title"]
        if not same_file:
            self._save_file(existing, entry, data, save=False)
            if isinstance(existing, Image):
                existing.renditions.all().delete()
        existing.save()
        self.counts["media_updated"] += 1
        return existing.pk

    @staticmethod
    def _save_file(media: Any, entry: dict[str, Any], data: bytes, save: bool = True) -> None:
        media.file.save(entry["filename"], ContentFile(data), save=False)
        if isinstance(media, Image):
            # Set dimensions after the file (saving the file resets them).
            media.width = entry["width"]
            media.height = entry["height"]
        if save:
            media.save()

    # -- pages -----------------------------------------------------------------

    def import_pages(self, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            model = apps.get_model(*entry["model"].split("."))
            if entry["model"] == HOME_LABEL:
                if self.mode == ImportMode.CREATE:
                    self.log("Home page kept as it is: there is one per site.")
                    self.counts["pages_skipped"] += 1
                    continue
                page = _home(model)
                self._apply_fields(page, entry, model)
                page.save()
                self.counts["pages_updated"] += 1
            else:
                parent = _parent(entry["parent_model"])
                siblings = model.objects.child_of(parent)
                existing = siblings.filter(slug=entry["slug"]).first()
                if existing is not None and self.mode == ImportMode.REPLACE:
                    page = existing
                    self._apply_fields(page, entry, model)
                    page.save()
                    self.counts["pages_updated"] += 1
                else:
                    page = model()
                    self._apply_fields(page, entry, model)
                    page.slug = _free_slug(parent, entry["slug"])
                    page.live = entry["live"]
                    parent.add_child(instance=page)
                    self.counts["pages_created"] += 1

            revision = page.save_revision()
            if entry["live"]:
                revision.publish()
            elif page.live:
                page.unpublish()
            self._sync_children(page, entry["children_relations"])

    def _apply_fields(self, page: Any, entry: dict[str, Any], model: type[Page]) -> None:
        page.title = entry["title"]
        page.slug = entry["slug"]
        if hasattr(page, "hero_image_id"):
            hero = entry["hero_image_pk"]
            page.hero_image_id = self.images.get(hero, hero) if hero else None
        for name, value in entry["fields"].items():
            setattr(page, name, deserialize_field(model, name, value))
        stream_block = model._meta.get_field("content").stream_block  # type: ignore[union-attr]
        page.content = stream_block.to_python(
            remap_media_ids(entry["content"], self.images, self.documents)
        )

    def _sync_children(self, page: Any, relations: dict[str, Any]) -> None:
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
                document = resource["document_pk"]
                PedagogyResource.objects.create(
                    page=page,
                    url=resource["url"],
                    document_id=self.documents.get(document, document) if document else None,
                    sort_order=resource["sort_order"],
                )


def _home(model: type[Page]) -> Page:
    page = model.objects.first()
    if page is None:
        raise ArchiveError(f"No {model.__name__} on this site: create it before importing.")
    return page


def _parent(label: str) -> Page:
    model = _PARENT_MODELS[label]  # checked by open_archive
    parent = model.objects.first()
    if parent is None:
        raise ArchiveError(f"No {model.__name__} on this site: create it before importing.")
    return parent


def _free_slug(parent: Page, slug: str) -> str:
    """``slug``, or ``slug-2``, ``slug-3``… if a sibling already has it."""
    taken = set(parent.get_children().values_list("slug", flat=True))
    candidate, number = slug, 1
    while candidate in taken:
        number += 1
        candidate = f"{slug}-{number}"
    return candidate


def _file_hash(media: Any) -> str | None:
    try:
        media.file.open("rb")
        try:
            return sha256_bytes(media.file.read())
        finally:
            media.file.close()
    except (FileNotFoundError, ValueError, OSError):
        return None


def _reset_media_sequences() -> None:
    """Realign the Image/Document id sequences after explicit-id inserts (PostgreSQL)."""
    statements = connection.ops.sequence_reset_sql(no_style(), [Image, Document])
    with connection.cursor() as cursor:
        for sql in statements:
            cursor.execute(sql)
