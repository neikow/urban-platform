"""Write the content archive: the transferred pages and the media they use."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any

from wagtail.documents.models import Document
from wagtail.images.models import Image

from home.models import HomePage
from pedagogy.models.pedagogy_card import PedagogyCardPage
from publications.models.event import EventPage
from publications.models.project import ProjectPage

from .archive import (
    ARCHIVE_VERSION,
    COMMON_PAGE_FIELDS,
    MANIFEST_NAME,
    PAGE_FIELD_SPECS,
    SIGNATURE_NAME,
    collect_media_ids,
    serialize_field,
    sha256_bytes,
    sign,
)

Log = Callable[[str], None]


def export_archive(
    output: str | Path | IO[bytes], key: str = "", log: Log = print
) -> dict[str, int]:
    """Write the archive to ``output``; signed when ``key`` is given. Returns the counts."""
    pages: list[dict[str, Any]] = []
    image_ids: set[int] = set()
    document_ids: set[int] = set()

    for page in _pages():
        entry, page_images, page_documents = _serialize_page(page)
        pages.append(entry)
        image_ids |= page_images
        document_ids |= page_documents

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        images = [e for pk in sorted(image_ids) if (e := _write_image(archive, pk, log))]
        documents = [e for pk in sorted(document_ids) if (e := _write_document(archive, pk, log))]
        manifest = json.dumps(
            {
                "version": ARCHIVE_VERSION,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "images": images,
                "documents": documents,
                "pages": pages,
            },
            indent=2,
            ensure_ascii=False,
        ).encode()
        archive.writestr(MANIFEST_NAME, manifest)
        if key:
            archive.writestr(SIGNATURE_NAME, sign(manifest, key))

    return {"pages": len(pages), "images": len(images), "documents": len(documents)}


def _pages() -> list[Any]:
    return [
        *HomePage.objects.all(),
        *ProjectPage.objects.all(),
        *EventPage.objects.all(),
        *PedagogyCardPage.objects.all(),
    ]


def _serialize_page(page: Any) -> tuple[dict[str, Any], set[int], set[int]]:
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


def _write_image(archive: zipfile.ZipFile, pk: int, log: Log) -> dict[str, Any] | None:
    image = Image.objects.filter(pk=pk).first()
    data = _read_file(image) if image else None
    if image is None or data is None:
        log(f"Skipping image pk={pk} (missing or unreadable)")
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


def _write_document(archive: zipfile.ZipFile, pk: int, log: Log) -> dict[str, Any] | None:
    document = Document.objects.filter(pk=pk).first()
    data = _read_file(document) if document else None
    if document is None or data is None:
        log(f"Skipping document pk={pk} (missing or unreadable)")
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


def _read_file(obj: Any) -> bytes | None:
    try:
        obj.file.open("rb")
        try:
            return obj.file.read()
        finally:
            obj.file.close()
    except (FileNotFoundError, ValueError, OSError):
        return None
