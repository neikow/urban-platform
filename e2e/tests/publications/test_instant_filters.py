import pytest
from playwright.sync_api import Page, expect


def results(page: Page):
    return page.locator("[data-instant-results] .grid > *")


@pytest.mark.e2e
def test_filters_and_search_update_the_list_without_reloading(page: Page, base_url: str):
    requests: dict[str, list[str]] = {"document": [], "fetch": []}
    page.on(
        "request",
        lambda request: requests.get(request.resource_type, []).append(request.url),
    )
    page.goto(base_url + "/actualites/")
    everything = results(page).count()

    page.locator("[data-instant-results] a", has_text="Projets").first.click()
    expect(page).to_have_url(base_url + "/actualites/?type=projects")
    expect(page.locator("[data-instant-status]")).to_contain_text("résultat")
    projects = results(page).count()
    assert 0 < projects < everything

    # Searching keeps the selected type.
    page.locator('input[type="search"]').fill("vote")
    expect(page).to_have_url(base_url + "/actualites/?type=projects&search=vote")
    expect(results(page)).not_to_have_count(projects)

    page.go_back()
    expect(page).to_have_url(base_url + "/actualites/")
    expect(results(page)).to_have_count(everything)
    expect(page.locator('input[type="search"]')).to_have_value("")

    assert len(requests["document"]) == 1
    # The list comes from the page's "results" route; the address bar shows the page.
    listing = [url for url in requests["fetch"] if "/actualites/" in url]
    assert listing
    assert all(url.startswith(base_url + "/actualites/results/") for url in listing)
