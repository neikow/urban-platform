"""Content fragment cache helpers and invalidation.

User-facing list pages (publications, pedagogy) and the home page's
``RecentPublicationsBlock`` cache their expensive, non-personalised render in a
dedicated cache alias (:data:`CONTENT_CACHE_ALIAS`). The whole alias is flushed
whenever any page is published or unpublished, so visitors never see stale
content — see :func:`clear_content_cache`, wired up in ``core.apps.CoreConfig``.

The alias lives in its own Redis DB (see settings) precisely because the flush
is wholesale; it must not share storage with sessions.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import InvalidCacheBackendError, caches
from django.core.cache.backends.base import BaseCache

CONTENT_CACHE_ALIAS = "content"

# Default TTL for content fragments (seconds). A short ceiling bounds staleness
# of time-relative bits (e.g. event "upcoming/past" badges) between publishes.
CONTENT_CACHE_TIMEOUT = 300

RECENT_PUBLICATIONS_KEY = "recent_publications:{count}"


def get_content_cache() -> BaseCache | None:
    """Return the content cache backend, or ``None`` if it is not configured."""
    try:
        return caches[CONTENT_CACHE_ALIAS]
    except InvalidCacheBackendError:
        return None


def clear_content_cache(**kwargs: Any) -> None:
    """Flush the content cache. Used as a Wagtail publish/unpublish receiver."""
    cache = get_content_cache()
    if cache is not None:
        cache.clear()
