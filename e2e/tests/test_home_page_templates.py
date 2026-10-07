from urllib.parse import urljoin

import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Page, expect

from e2e.utils import login_user

HOW_IT_WORKS = "Quatre étapes pour peser sur les projets"  # only in the "Participation" template


def open_home_page_editor(page: Page, base_url: str) -> None:
    # The user bar on the home page links to its editor.
    page.goto(base_url + "/")
    edit_url = page.locator("wagtail-userbar a[href$='/edit/']").first.get_attribute("href")
    page.goto(urljoin(base_url + "/", edit_url))


def apply_template(page: Page, name: str) -> None:
    page.get_by_role("button", name=_("Actions")).first.click()
    page.get_by_role("link", name=_("Start from a template")).click()
    page.get_by_role("button", name=_("Use “%(name)s”") % {"name": name}).click()
    expect(page.locator(".messages .success, .w-message--success").first).to_be_visible()


def publish(page: Page) -> None:
    page.get_by_role("button", name=_("More actions")).first.click()
    page.get_by_role("button", name=_("Publish")).click()
    expect(page.locator(".messages .success, .w-message--success").first).to_be_visible()


@pytest.mark.e2e
def test_editor_builds_the_home_page_from_a_template(
    page: Page, base_url: str, admin_email: str, admin_password: str
):
    login_user(page=page, base_url=base_url, email=admin_email, password=admin_password)
    open_home_page_editor(page, base_url)
    apply_template(page, _("Essentials"))
    publish(page)

    open_home_page_editor(page, base_url)
    apply_template(page, _("Participation"))

    # A draft: the website does not change before publishing.
    page.goto(base_url + "/")
    expect(page.get_by_role("heading", name="Votre avis compte")).to_be_visible()
    expect(page.get_by_role("heading", name=HOW_IT_WORKS)).to_have_count(0)

    open_home_page_editor(page, base_url)
    publish(page)

    page.goto(base_url + "/")
    expect(page.get_by_role("heading", name=HOW_IT_WORKS)).to_be_visible()
    expect(page.get_by_role("heading", name="Consultations en cours")).to_be_visible()
