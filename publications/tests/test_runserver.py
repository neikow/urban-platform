import pytest
from django.test import RequestFactory

from publications.management.commands.runserver import serve_range


@pytest.fixture
def archive(tmp_path, settings):
    settings.STATICFILES_DIRS = [tmp_path]
    (tmp_path / "tiles.pmtiles").write_bytes(bytes(range(100)))
    return "tiles.pmtiles"


def get(headers):
    return RequestFactory().get("/static/tiles.pmtiles", headers=headers)


def test_serves_the_requested_bytes(archive):
    response = serve_range(get({"Range": "bytes=10-19"}), archive)

    assert response.status_code == 206
    assert response.content == bytes(range(10, 20))
    assert response["Content-Range"] == "bytes 10-19/100"


def test_open_ended_range_stops_at_the_end_of_the_file(archive):
    response = serve_range(get({"Range": "bytes=90-"}), archive)

    assert response.content == bytes(range(90, 100))
    assert response["Content-Range"] == "bytes 90-99/100"


def test_range_past_the_end_is_not_satisfiable(archive):
    response = serve_range(get({"Range": "bytes=200-300"}), archive)

    assert response.status_code == 416
    assert response["Content-Range"] == "bytes */100"


def test_no_range_falls_back_to_the_staticfiles_view(archive):
    assert serve_range(get({}), archive) is None
