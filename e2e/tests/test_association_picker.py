import json

import pytest
from playwright.sync_api import Page, Route, expect

# Next to the Vallon des Auffes seat (scripts/e2e.py), far from the Catalans one.
AUFFES_LABEL = "150 Rue du Vallon des Auffes 13007 Marseille"
AUFFES_ADDRESS = {
    "label": AUFFES_LABEL,
    "postcode": "13007",
    "lon": 5.3495,
    "lat": 43.2851,
    "score": 0.97,
}


def suggest_auffes(route: Route) -> None:
    route.fulfill(content_type="application/json", body=json.dumps({"results": [AUFFES_ADDRESS]}))


def choose_on_the_map(page: Page, name: str) -> None:
    page.locator("[data-picker-open]").click()
    dialog = page.locator("[data-picker-dialog]")
    expect(dialog).to_be_visible()
    dialog.locator("[data-picker-list] button", has_text=name).click()
    dialog.locator("[data-picker-confirm]").click()
    expect(dialog).to_be_hidden()


@pytest.mark.e2e
def test_picking_an_address_selects_the_nearest_association(page: Page, base_url: str):
    # The geocoding service is not reached from the tests.
    page.route("**/api/addresses/?*", suggest_auffes)
    page.goto(base_url + "/auth/register/")

    address = page.locator("address-input input")
    address.press_sequentially("150 rue du vallon")
    page.get_by_role("option", name=AUFFES_LABEL).click()

    # The dropdown gives way to the button opening the map.
    expect(page.locator("association-select select")).to_be_hidden()
    opener = page.locator("[data-picker-open]")
    expect(opener).to_contain_text("Vallon des Auffes · ")
    expect(opener).to_contain_text(" m")
    expect(page.locator('input[name="postal_code"]')).to_have_value("13007")

    # A choice made on the map is kept when the address changes again.
    choose_on_the_map(page, "Pharo Catalans")
    expect(opener).to_contain_text("Pharo Catalans")
    address.fill("")
    address.press_sequentially("150 rue du vallon")
    page.get_by_role("option", name=AUFFES_LABEL).click()
    expect(opener).to_contain_text("Pharo Catalans")
    expect(page.locator("association-select select option:checked")).to_contain_text(
        "Pharo Catalans"
    )

    # Ticking "no CIQ" disables the picker.
    page.locator("[data-no-association]").check()
    expect(opener).to_be_disabled()
    page.locator("[data-no-association]").uncheck()
    expect(opener).to_be_enabled()


@pytest.mark.e2e
def test_map_picker_on_a_phone(page: Page, base_url: str):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/auth/register/")

    page.locator("[data-picker-open]").click()
    dialog = page.locator("[data-picker-dialog]")
    expect(dialog.locator(".leaflet-container")).to_be_visible()
    # The seats are on the map; tapping one selects it in the list.
    dialog.locator(".map-ciq-seat").first.click()
    expect(dialog.locator("[data-picker-list] button[aria-pressed=true]")).to_have_count(1)

    # Cancelling keeps the previous value.
    dialog.locator("footer [data-picker-close]").click()
    expect(dialog).to_be_hidden()
    expect(page.locator("association-select select")).to_have_value("")

    choose_on_the_map(page, "Vallon des Auffes")
    expect(page.locator("[data-picker-open]")).to_contain_text("Vallon des Auffes")
