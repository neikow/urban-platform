import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Page, expect

from e2e.utils import login_user

EVENT_PATH = "/actualites/fete-du-quartier/"


@pytest.mark.e2e
def test_flag_event_as_interesting(
    page: Page, base_url: str, voter_email: str, voter_password: str
):
    login_user(page=page, base_url=base_url, email=voter_email, password=voter_password)
    page.goto(base_url + EVENT_PATH)

    button = page.locator("#event-interest-btn")
    expect(button).to_have_attribute("aria-pressed", "false")

    button.click()
    expect(button).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#event-interest-count")).to_contain_text("1")

    page.goto(base_url + "/auth/me/")
    expect(page.get_by_role("link", name="Fête du quartier")).to_be_visible()

    page.goto(base_url + EVENT_PATH)
    page.locator("#event-interest-btn").click()
    expect(page.locator("#event-interest-btn")).to_have_attribute("aria-pressed", "false")


@pytest.mark.e2e
def test_anonymous_visitor_is_asked_to_log_in(page: Page, base_url: str):
    page.goto(base_url + EVENT_PATH)

    page.get_by_role("button", name=_("I'm interested")).click()

    expect(page.locator("#login_modal")).to_be_visible()


@pytest.mark.e2e
def test_event_calendar_download(page: Page, base_url: str):
    page.goto(base_url + EVENT_PATH)

    with page.expect_download() as download_info:
        page.get_by_role("link", name=_("Add to my calendar")).click()

    assert download_info.value.suggested_filename == "fete-du-quartier.ics"
