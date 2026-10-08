import pytest
from django.test import RequestFactory

from django.http import Http404

from publications.management.commands.runserver import serve_media_tiles, serve_range


@pytest.fixture
def archive(tmp_path):
    path = tmp_path / "tiles.pmtiles"
    path.write_bytes(bytes(range(100)))
    return path


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


class TestMediaTiles:
    @pytest.fixture(autouse=True)
    def media(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "map-tiles").mkdir()
        (tmp_path / "map-tiles" / "local-area.pmtiles").write_bytes(bytes(range(100)))

    def test_serves_ranges(self):
        request = RequestFactory().get(
            "/media/map-tiles/local-area.pmtiles", headers={"Range": "bytes=0-9"}
        )

        response = serve_media_tiles(request, "map-tiles/local-area.pmtiles")

        assert response.status_code == 206
        assert response.content == bytes(range(10))

    def test_serves_whole_file_without_range(self):
        request = RequestFactory().get("/media/map-tiles/local-area.pmtiles")

        response = serve_media_tiles(request, "map-tiles/local-area.pmtiles")

        assert response.status_code == 200

    @pytest.mark.parametrize("path", ["map-tiles/missing.pmtiles", "../outside.pmtiles"])
    def test_unknown_or_outside_files(self, path):
        with pytest.raises(Http404):
            serve_media_tiles(RequestFactory().get("/media/x"), path)
