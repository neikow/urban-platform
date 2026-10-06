import pytest
from playwright.sync_api import Page, expect

from e2e.utils import login_user


@pytest.mark.e2e
def test_admin_places_project_on_map(
    page: Page, base_url: str, admin_email: str, admin_password: str
):
    login_user(page=page, base_url=base_url, email=admin_email, password=admin_password)
    page.goto(f"{base_url}/actualites/projet-vote/")
    project_id = page.locator("#vote-component").get_attribute("data-project-id")
    page.goto(f"{base_url}/admin/pages/{project_id}/edit/")

    widget = page.locator("geojson-map-input")
    widget.scroll_into_view_if_needed()
    expect(widget.locator(".leaflet-container")).to_be_visible()

    # Geoman toolbar: place a marker, then click in the middle of the map.
    widget.locator(".leaflet-pm-icon-marker").click()
    widget.locator("[data-map]").click()
    expect(widget.locator(".leaflet-marker-icon")).to_have_count(1)

    value = widget.locator("textarea").input_value()
    assert '"type":"Point"' in value

    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()
    expect(page.locator(".messages .success, .w-message--success").first).to_be_visible()

    page.goto(f"{base_url}/actualites/projet-vote/")
    expect(page.locator("#project-location-map .leaflet-interactive")).to_have_count(1)

    page.goto(f"{base_url}/actualites/")
    expect(page.locator("#projects-map .leaflet-interactive.map-project").first).to_be_visible()


@pytest.mark.e2e
def test_map_tiles_are_self_hosted(page: Page, base_url: str):
    """The basemap is read from our own PMTiles archive, with range requests."""
    tile_requests = []
    page.on(
        "request",
        lambda request: (
            tile_requests.append(request) if request.resource_type in ("fetch", "image") else None
        ),
    )

    page.goto(base_url + "/actualites/")
    page.locator("#projects-map .leaflet-tile-loaded").first.wait_for()

    assert tile_requests
    assert all(request.url.startswith(base_url) for request in tile_requests)
    archive = [r for r in tile_requests if r.url.endswith(".pmtiles")]
    assert archive
    assert all(r.headers.get("range", "").startswith("bytes=") for r in archive)
