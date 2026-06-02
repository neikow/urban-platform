"""Tests for the content fragment cache and its publish-time invalidation.

The test settings use a DummyCache for the ``content`` alias (caching is a
no-op for the rest of the suite); these tests swap in a real in-memory cache to
exercise the caching and invalidation paths.
"""

import pytest
from django.core.cache import caches
from django.test import Client

from core.blocks import RecentPublicationsBlock
from core.cache import RECENT_PUBLICATIONS_KEY
from pedagogy.models.pedagogy_index import PedagogyIndexPage
from publications.models.publication_index import PublicationIndexPage

_LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache", "LOCATION": ""},
    "content": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture
def locmem_content_cache(settings):
    settings.CACHES = _LOCMEM_CACHES
    caches["content"].clear()
    yield
    caches["content"].clear()


@pytest.mark.django_db
def test_publishing_a_page_flushes_content_cache(locmem_content_cache):
    cache = caches["content"]
    cache.set("sentinel", "value", 300)
    assert cache.get("sentinel") == "value"

    index = PublicationIndexPage.objects.get()
    index.save_revision().publish()

    assert cache.get("sentinel") is None


@pytest.mark.django_db
def test_unpublishing_a_page_flushes_content_cache(locmem_content_cache):
    cache = caches["content"]
    index = PublicationIndexPage.objects.get()
    cache.set("sentinel", "value", 300)

    index.unpublish()

    assert cache.get("sentinel") is None


@pytest.mark.django_db
def test_recent_publications_block_caches_query(locmem_content_cache):
    block = RecentPublicationsBlock()
    cache_key = RECENT_PUBLICATIONS_KEY.format(count=5)
    assert caches["content"].get(cache_key) is None

    context = block.get_context({"number_of_publications": 5})

    assert isinstance(context["publications"], list)
    # The query result is now memoised in the content cache.
    assert caches["content"].get(cache_key) is not None


@pytest.mark.django_db
def test_publication_index_renders_with_cache_tag(client: Client):
    # Smoke test: the {% cache %} fragment tag loads and renders (content alias
    # is a DummyCache here, so the fragment is simply re-rendered).
    index = PublicationIndexPage.objects.get()
    response = client.get(index.url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_pedagogy_index_renders_with_cache_tag(client: Client):
    index = PedagogyIndexPage.objects.get()
    response = client.get(index.url)
    assert response.status_code == 200
