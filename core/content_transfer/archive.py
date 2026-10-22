"""The content archive: what moves between environments, and how it is checked.

Publications (projects, events), pedagogy cards and the home page move between
environments (production → staging) with the images and documents they use,
in a ``.zip``: a ``manifest.json`` and the media files.

* **Two import modes.** "Replace" keeps media primary keys (StreamField and
  rich text refer to media by id) and updates pages with the same slug under
  the same index page. "Create" never changes what exists: media whose id is
  taken by another file get a new id, references are rewritten
  (:func:`remap_media_ids`), and every page is created anew.
* **Authenticity.** With ``CONTENT_TRANSFER_KEY`` set (the same on both
  sides), the manifest is signed (HMAC-SHA256) on export and the signature is
  required on import. The manifest holds each file's SHA-256, checked too.
* **Untrusted input.** An archive is checked before anything is read from it:
  member names, sizes, the page models and the media extensions it may contain.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import zipfile
from datetime import datetime
from typing import Any

from django.db import models

# Module names of the page types this tool transfers, keyed by ``label_lower``.
PROJECT_LABEL = "publications.projectpage"
EVENT_LABEL = "publications.eventpage"
PEDAGOGY_CARD_LABEL = "pedagogy.pedagogycardpage"
# Singleton (max_count=1) site root; upserted in place rather than by slug under
# a parent index, since it lives directly under the Wagtail tree root.
HOME_LABEL = "home.homepage"

# Concrete, non-tree scalar fields exported per page model (common Page fields
# such as title/slug/seo are handled separately).
PAGE_FIELD_SPECS: dict[str, list[str]] = {
    PROJECT_LABEL: [
        "description",
        "category",
        "participation_mode",
        "voting_end_date",
        "show_toc",
    ],
    EVENT_LABEL: [
        "description",
        "event_date",
        "end_date",
        "location",
        "address",
        "is_online",
        "online_link",
        "max_participants",
    ],
    PEDAGOGY_CARD_LABEL: [
        "description",
        "show_toc",
    ],
}

COMMON_PAGE_FIELDS = ["seo_title", "search_description", "show_in_menus"]

# StreamField struct keys that hold an image / document chooser id.
_IMAGE_KEYS = {"image", "author_image"}
_DOCUMENT_KEYS = {"document"}

# Rich-text embeds/links carry ids as ``embedtype="image" ... id="N"`` (in
# either attribute order), and document links as ``linktype="document"``.
_IMAGE_EMBED_RES = [
    re.compile(r'embedtype="image"[^>]*?\bid="(\d+)"'),
    re.compile(r'\bid="(\d+)"[^>]*?embedtype="image"'),
]
_DOCUMENT_LINK_RES = [
    re.compile(r'linktype="document"[^>]*?\bid="(\d+)"'),
    re.compile(r'\bid="(\d+)"[^>]*?linktype="document"'),
]

ARCHIVE_VERSION = 1
MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "manifest.sig"

# Page models an archive may create, and the index pages they may go under.
TRANSFERRED_MODELS = {HOME_LABEL, PROJECT_LABEL, EVENT_LABEL, PEDAGOGY_CARD_LABEL}
PARENT_MODELS = {"publications.publicationindexpage", "pedagogy.pedagogyindexpage"}

# Limits against archives that would fill the disk or the memory.
MAX_MEMBERS = 20_000
MAX_TOTAL_SIZE = 4 * 1024**3
MAX_MANIFEST_SIZE = 200 * 1024**2
MAX_COMPRESSION_RATIO = 200

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "avif"}


class ArchiveError(Exception):
    """The archive is unreadable, unsigned, tampered with or not one of ours."""


def collect_media_ids(raw_content: Any) -> tuple[set[int], set[int]]:
    """Return ``(image_ids, document_ids)`` referenced anywhere in ``raw_content``.

    Walks the StreamField raw data generically (so nested blocks such as
    two-column layouts and list blocks are covered) and scans embedded rich
    text for image embeds and document links.
    """
    image_ids: set[int] = set()
    document_ids: set[int] = set()
    _walk(raw_content, image_ids, document_ids)
    return image_ids, document_ids


def _walk(node: Any, image_ids: set[int], document_ids: set[int]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _IMAGE_KEYS and isinstance(value, int):
                image_ids.add(value)
            elif key in _DOCUMENT_KEYS and isinstance(value, int):
                document_ids.add(value)
            else:
                _walk(value, image_ids, document_ids)
    elif isinstance(node, list):
        for item in node:
            _walk(item, image_ids, document_ids)
    elif isinstance(node, str):
        for regex in _IMAGE_EMBED_RES:
            image_ids.update(int(m) for m in regex.findall(node))
        for regex in _DOCUMENT_LINK_RES:
            document_ids.update(int(m) for m in regex.findall(node))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialize_field(page: models.Model, name: str) -> Any:
    """Return a JSON-serialisable value for ``page.<name>``."""
    value = getattr(page, name)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def deserialize_field(model: type[models.Model], name: str, value: Any) -> Any:
    """Inverse of :func:`serialize_field`, using the field type to coerce."""
    field = model._meta.get_field(name)
    if isinstance(field, models.DateTimeField) and value is not None:
        return datetime.fromisoformat(value)
    return value


def remap_media_ids(raw: Any, images: dict[int, int], documents: dict[int, int]) -> Any:
    """``raw`` StreamField data with media ids replaced as the maps say (others kept)."""
    if not images and not documents:
        return raw
    if isinstance(raw, dict):
        result = {}
        for key, value in raw.items():
            if key in _IMAGE_KEYS and isinstance(value, int):
                result[key] = images.get(value, value)
            elif key in _DOCUMENT_KEYS and isinstance(value, int):
                result[key] = documents.get(value, value)
            else:
                result[key] = remap_media_ids(value, images, documents)
        return result
    if isinstance(raw, list):
        return [remap_media_ids(item, images, documents) for item in raw]
    if isinstance(raw, str):
        return _remap_rich_text(raw, images, documents)
    return raw


_EMBED_TAG_RE = re.compile(r"<(?:embed|a)\b[^>]*>")
_ID_RE = re.compile(r'\bid="(\d+)"')


def _remap_rich_text(html: str, images: dict[int, int], documents: dict[int, int]) -> str:
    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if 'embedtype="image"' in tag:
            mapping = images
        elif 'linktype="document"' in tag:
            mapping = documents
        else:
            return tag
        return _ID_RE.sub(lambda m: f'id="{mapping.get(int(m.group(1)), int(m.group(1)))}"', tag)

    return _EMBED_TAG_RE.sub(replace, html)


# --- signing --------------------------------------------------------------------


def sign(manifest: bytes, key: str) -> str:
    return hmac.new(key.encode(), manifest, hashlib.sha256).hexdigest()


def verify(manifest: bytes, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign(manifest, key), signature.strip())


# --- reading --------------------------------------------------------------------


def _extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def open_archive(path: Any, key: str = "") -> tuple[zipfile.ZipFile, dict[str, Any]]:
    """Open and check an archive; returns it with its manifest. Raises ArchiveError.

    With ``key``, the manifest must carry a valid signature. Every file the
    manifest names must be in the archive, with the announced SHA-256 (checked
    as it is read, by :func:`read_member`).
    """
    from django.conf import settings

    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ArchiveError(f"Not a zip archive: {error}") from error
    try:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ArchiveError("Too many files in the archive.")
        total = 0
        for info in infos:
            name = info.filename
            if name.startswith("/") or "\\" in name or ".." in name.split("/"):
                raise ArchiveError(f"Unsafe file name in the archive: {name!r}")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise ArchiveError(f"Suspicious compression for {name!r}.")
            total += info.file_size
        if total > MAX_TOTAL_SIZE:
            raise ArchiveError("The archive is too large once extracted.")

        try:
            info = archive.getinfo(MANIFEST_NAME)
        except KeyError as error:
            raise ArchiveError("The archive has no manifest.") from error
        if info.file_size > MAX_MANIFEST_SIZE:
            raise ArchiveError("The manifest is too large.")
        raw_manifest = archive.read(MANIFEST_NAME)

        if key:
            try:
                signature = archive.read(SIGNATURE_NAME).decode()
            except (KeyError, UnicodeDecodeError) as error:
                raise ArchiveError("The archive is not signed.") from error
            if not verify(raw_manifest, signature, key):
                raise ArchiveError(
                    "The archive signature is wrong: it was changed, or comes from elsewhere."
                )

        try:
            manifest = json.loads(raw_manifest)
        except ValueError as error:
            raise ArchiveError("The manifest is not valid JSON.") from error
        _check_manifest(manifest, set(archive.namelist()), settings)
    except ArchiveError:
        archive.close()
        raise
    return archive, manifest


def _check_manifest(manifest: Any, names: set[str], settings: Any) -> None:
    if not isinstance(manifest, dict) or manifest.get("version") != ARCHIVE_VERSION:
        raise ArchiveError("Unsupported archive version.")
    for key in ("images", "documents", "pages"):
        if not isinstance(manifest.get(key), list):
            raise ArchiveError(f"The manifest has no {key} list.")

    document_extensions = {e.lower() for e in getattr(settings, "WAGTAILDOCS_EXTENSIONS", [])}
    for kind, allowed in (("images", IMAGE_EXTENSIONS), ("documents", document_extensions)):
        for entry in manifest[kind]:
            if not isinstance(entry, dict) or not isinstance(entry.get("pk"), int):
                raise ArchiveError(f"Invalid {kind} entry.")
            if entry.get("file") not in names:
                raise ArchiveError(f"Missing file {entry.get('file')!r}.")
            filename = str(entry.get("filename", ""))
            if (
                "/" in filename
                or "\\" in filename
                or (allowed and _extension(filename) not in allowed)
            ):
                raise ArchiveError(f"File type not allowed: {filename!r}")

    for entry in manifest["pages"]:
        if not isinstance(entry, dict) or entry.get("model") not in TRANSFERRED_MODELS:
            raise ArchiveError(
                f"Page type not allowed: {entry.get('model') if isinstance(entry, dict) else entry!r}"
            )
        if entry["model"] != HOME_LABEL and entry.get("parent_model") not in PARENT_MODELS:
            raise ArchiveError(f"Parent page type not allowed: {entry.get('parent_model')!r}")


def read_member(archive: zipfile.ZipFile, entry: dict[str, Any]) -> bytes:
    """The bytes of a media file, checked against the manifest's SHA-256."""
    data = archive.read(entry["file"])
    if sha256_bytes(data) != entry.get("sha256"):
        raise ArchiveError(f"{entry['file']!r} does not match its checksum.")
    return data
