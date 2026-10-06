import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Page, expect

from e2e.utils import login_user

PROJECT_PATH = "/actualites/projet-a-clore/"


@pytest.mark.e2e
def test_editor_closes_a_poll(page: Page, base_url: str, admin_email: str, admin_password: str):
    login_user(page=page, base_url=base_url, email=admin_email, password=admin_password)
    page.goto(base_url + PROJECT_PATH)
    expect(page.locator("#vote-final-results")).to_have_count(0)
    project_id = page.locator("#vote-component").get_attribute("data-project-id")

    page.goto(f"{base_url}/admin/pages/{project_id}/edit/")
    page.get_by_role("button", name=_("Actions")).first.click()
    page.get_by_role("link", name=_("Close the poll and send the results")).click()

    expect(page.get_by_text(_("This cannot be undone."))).to_be_visible()
    page.get_by_role("button", name=_("Close the poll and send the results")).click()

    page.goto(base_url + PROJECT_PATH)
    expect(page.locator("#vote-final-results")).to_be_visible()
