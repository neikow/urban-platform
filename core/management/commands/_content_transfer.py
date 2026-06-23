"""Shared helpers for the ``export_content`` / ``import_content`` commands.

These move publications (projects, events) and pedagogy cards — together with
the images and documents they reference — between environments (e.g. staging
↔ prod) via a portable ``.zip`` archive.

Design notes
------------
* **Media is imported preserving its original primary key.** Image and document
  references live inside StreamField data and rich text by integer id; keeping
  the same pk on the destination means every reference stays valid without any
  rewriting. This assumes the two environments share a media identity space
  (the normal case when staging is seeded from prod, or vice versa): a re-import
  updates the matching pk in place. See :func:`upsert_image` / :func:`upsert_document`.
* **Pages are upserted by slug** under the (single) index page of the matching
  type, so repeated imports converge rather than duplicate.

The module name is prefixed with ``_`` so Django does not treat it as a
management command.
"""

from __future__ import annotations

import hashlib
import re
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
