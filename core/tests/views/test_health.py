from unittest import mock

import pytest
from django.db import DatabaseError


@pytest.mark.django_db
def test_healthz_ok(client, settings):
    settings.APP_VERSION = "1.4.0"

    response = client.get("/healthz/")

    assert response.status_code == 200
    # The deployment agent reads the version to confirm an update.
    assert response.json() == {"status": "ok", "version": "1.4.0"}


@pytest.mark.django_db
def test_healthz_reports_database_failure(client):
    with mock.patch("core.views.health.connection.ensure_connection", side_effect=DatabaseError):
        response = client.get("/healthz/")

    assert response.status_code == 503
