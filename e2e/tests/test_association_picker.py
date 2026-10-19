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


@pytest.mark.e2e
def test_picking_an_address_selects_the_nearest_association(page: Page, base_url: str):
    # The geocoding service is not reached from the tests.
    page.route("**/api/addresses/?*", suggest_auffes)
    page.goto(base_url + "/auth/register/")

    address = page.locator("address-input input")
    address.press_sequentially("150 rue du vallon")
    page.get_by_role("option", name=AUFFES_LABEL).click()

    association = page.locator("association-select select")
    selected = association.locator("option:checked")
    expect(selected).to_contain_text("Vallon des Auffes · ")
    expect(selected).to_contain_text(" m")
    expect(page.locator('input[name="postal_code"]')).to_have_value("13007")

    # A choice is kept when the address changes again.
    association.select_option(
        label=association.locator("option", has_text="Pharo Catalans").inner_text()
    )
    address.fill("")
    address.press_sequentially("150 rue du vallon")
    page.get_by_role("option", name=AUFFES_LABEL).click()
    expect(association.locator("option:checked")).to_contain_text("Pharo Catalans")
