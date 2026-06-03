"""Rate-limiting tests for the auth endpoints.

The test/e2e settings use a DummyCache, under which django-ratelimit is a
no-op (so the rest of the suite is unaffected). These tests swap in a real
in-memory cache via the ``settings`` fixture to exercise the throttling path.
"""

import pytest
from django.core.cache import cache
from django.test import Client

_LOCMEM_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture
def locmem_ratelimit(settings, monkeypatch):
    """Enable a real cache so django-ratelimit actually counts, then reset it.

    django-ratelimit buckets counts into fixed wall-clock windows
    (``_get_window``). On a loaded CI runner the handful of POSTs in these
    tests can straddle a window boundary, resetting the count and making the
    throttle assertion flaky. Pin the window to a constant so every request in
    a test shares one bucket.
    """
    settings.CACHES = _LOCMEM_CACHE
    monkeypatch.setattr("django_ratelimit.core._get_window", lambda value, period: 1)
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_login_throttled_after_limit(client: Client, locmem_ratelimit):
    from django.urls import reverse

    url = reverse("login")
    payload = {"modal-email": "nobody@example.com", "modal-password": "WrongPass123"}

    # The limit is 5/m. The first five are allowed (bad creds -> 400);
    # the sixth is blocked with 429.
    for _ in range(5):
        response = client.post(url, data=payload)
        assert response.status_code == 400

    blocked = client.post(url, data=payload)
    assert blocked.status_code == 429
    assert blocked.json()["success"] is False


@pytest.mark.django_db
def test_password_reset_throttled_after_limit(client: Client, locmem_ratelimit):
    from django.urls import reverse

    url = reverse("password_reset_request")
    payload = {"email": "someone@example.com"}

    # The limit is 5/h. First five succeed (302 redirect to "sent").
    for _ in range(5):
        response = client.post(url, data=payload)
        assert response.status_code == 302

    blocked = client.post(url, data=payload)
    assert blocked.status_code == 200  # re-rendered form with error
    assert b"Trop de demandes" in blocked.content


@pytest.mark.django_db
def test_register_throttled_after_limit(client: Client, locmem_ratelimit):
    from django.urls import reverse

    url = reverse("register")
    # Deliberately invalid payload so no users are created; the rate limiter
    # still counts every POST.
    payload = {"email": "not-an-email"}

    for _ in range(10):
        response = client.post(url, data=payload)
        assert response.status_code == 200

    blocked = client.post(url, data=payload)
    assert blocked.status_code == 200
    # Apostrophe is HTML-escaped in the rendered template, so match the
    # ASCII-only prefix.
    assert b"Trop de tentatives" in blocked.content
