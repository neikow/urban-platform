import re

import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Browser, Page, expect

from e2e.utils import login_user


@pytest.mark.e2e
def test_admin_publishes_an_announcement_visitors_can_close(
    page: Page, browser: Browser, base_url: str, admin_email: str, admin_password: str
):
    login_user(page=page, base_url=base_url, email=admin_email, password=admin_password)
    page.goto(base_url + "/admin/settings/core/announcement/")
    page.get_by_role("checkbox", name=_("Show the announcement")).check()
    editor = page.locator(".public-DraftEditor-content")
    editor.click()
    editor.press_sequentially("Réunion publique jeudi à 18h")
    # Draftail serialises into its hidden input after a short delay.
    expect(page.locator("input[name=message]")).to_have_value(re.compile("jeudi à 18h"))
    page.get_by_role("button", name=_("Save")).click()
    expect(page.locator(".messages .success, .w-message--success").first).to_be_visible()

    # A visitor, in a fresh browser context.
    visitor = browser.new_page(base_url=base_url)
    visitor.goto("/")
    band = visitor.get_by_role("region", name=_("Announcement"))
    expect(band).to_contain_text("Réunion publique jeudi à 18h")

    band.get_by_role("button", name=_("Close the announcement")).click()
    expect(band).to_have_count(0)
    visitor.reload()
    expect(visitor.get_by_role("region", name=_("Announcement"))).to_have_count(0)

    # Changing the message shows it again.
    page.goto(base_url + "/admin/settings/core/announcement/")
    editor.click()
    editor.press("End")
    editor.press_sequentially(", salle des fêtes")
    expect(page.locator("input[name=message]")).to_have_value(re.compile("salle des fêtes"))
    page.get_by_role("button", name=_("Save")).click()
    expect(page.locator(".messages .success, .w-message--success").first).to_be_visible()

    visitor.reload()
    expect(visitor.get_by_role("region", name=_("Announcement"))).to_contain_text("salle des fêtes")
    visitor.close()
