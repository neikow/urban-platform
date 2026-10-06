from unittest import mock

import pytest
from django.db import DatabaseError


@pytest.mark.django_db
def test_healthz_ok(client):
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_healthz_reports_database_failure(client):
    with mock.patch("core.views.health.connection.ensure_connection", side_effect=DatabaseError):
        response = client.get("/healthz/")

    assert response.status_code == 503
