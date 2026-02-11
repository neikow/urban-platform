"""
E2E Test Configuration.

This module configures pytest for E2E tests that run against a real Django server.
The server should be started separately using `python scripts/e2e.py serve`.
The database persists between test runs to simulate real user interactions.
"""

import os
import sys
import django
import pytest

# Server configuration
E2E_SERVER_HOST = "127.0.0.1"
E2E_SERVER_PORT = 8001
E2E_BASE_URL = f"http://{E2E_SERVER_HOST}:{E2E_SERVER_PORT}"


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest for E2E tests."""
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "urban_platform.settings.e2e")

    # Initialize Django so we can use Django utilities like reverse()
    if not django.apps.apps.ready:
        django.setup()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the base URL of the E2E server."""
    return E2E_BASE_URL


# Test user credentials - these should match what's created by scripts/e2e.py
@pytest.fixture
def user_email() -> str:
    """Default test user email."""
    return "e2e.user@email.com"


@pytest.fixture
def user_password() -> str:
    """Default test user password."""
    return "password123"


@pytest.fixture
def admin_email() -> str:
    """Admin test user email."""
    return "e2e.admin@email.com"


@pytest.fixture
def admin_password() -> str:
    """Admin test user password."""
    return "password123"
