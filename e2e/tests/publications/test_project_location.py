import re

import pytest
from playwright.sync_api import Geolocation, Page, expect

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


# Seeded by scripts/e2e.py on the "Projet ouvert aux idées" project.
PHARO: Geolocation = {"latitude": 43.2925, "longitude": 5.3615}
PARIS: Geolocation = {"latitude": 48.8566, "longitude": 2.3522}


@pytest.mark.e2e
def test_project_popup_keeps_the_category_on_one_line(page: Page, base_url: str):
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation(PHARO)
    page.goto(f"{base_url}/actualites/")

    # Locate the user on the seeded project, then click it through the
    # (non-interactive) position circle once the zoom animation is over.
    page.get_by_role("button", name="Afficher ma position").click()
    me = page.locator("#projects-map .map-me")
    expect(me).to_be_visible()
    expect(page.locator("#projects-map")).not_to_have_class(re.compile("leaflet-zoom-anim"))
    box = me.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    popup = page.locator(".map-popup")
    expect(popup.locator(".map-popup__title")).to_have_text("Projet ouvert aux idées")
    popup_box = popup.bounding_box()
    assert popup_box is not None
    assert popup_box["width"] >= 260  # truncating the category must not shrink the card
    category = popup.locator(".map-popup__category")
    expect(category).to_have_attribute("title", "Cadre de vie / Espaces Publics / Mobilité")
    line_height = category.evaluate("el => parseFloat(getComputedStyle(el).lineHeight)")
    box = category.bounding_box()
    assert box is not None
    assert box["height"] <= line_height + 1
    expect(popup.locator(".map-popup__status")).to_be_visible()
    expect(popup.locator(".map-popup__link")).to_have_attribute("href", "/actualites/projet-idees/")


@pytest.mark.e2e
def test_locating_outside_marseille_says_so(page: Page, base_url: str):
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation(PARIS)
    page.goto(f"{base_url}/actualites/")

    page.get_by_role("button", name="Afficher ma position").click()
    expect(page.locator("#projects-map ~ [role=status]")).to_have_text(
        "Vous êtes en dehors de Marseille : la carte ne couvre que la ville."
    )
    expect(page.locator("#projects-map .map-me")).to_have_count(0)


@pytest.mark.e2e
def test_locating_inside_marseille_shows_the_position(page: Page, base_url: str):
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation(PHARO)
    page.goto(f"{base_url}/actualites/")

    page.get_by_role("button", name="Afficher ma position").click()
    expect(page.locator("#projects-map .map-me")).to_be_visible()
    expect(page.locator("#projects-map .leaflet-tooltip")).to_have_text("Vous êtes ici")
    expect(page.locator("#projects-map ~ [role=status]")).to_have_text("")
