import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Page, expect

from e2e.utils import login_user


@pytest.mark.e2e
def test_editor_creates_a_project_from_a_template(
    page: Page, base_url: str, admin_email: str, admin_password: str
):
    login_user(page=page, base_url=base_url, email=admin_email, password=admin_password)
    page.goto(base_url + "/admin/")
    page.get_by_role("button", name="Actualités").click()
    page.get_by_role("link", name="Ajouter").click()
    page.get_by_role("link", name=_("Project"), exact=True).click()

    expect(page.get_by_role("heading", name=_("Project put to the vote"))).to_be_visible()
    page.get_by_role(
        "link", name=_("Use “%(name)s”") % {"name": _("Project open to ideas")}
    ).click()

    # The editor opens with the template's sections and participation mode.
    expect(page.get_by_text("Sur quoi vos idées sont attendues")).to_be_visible()
    expect(page.locator("select[name=participation_mode]")).to_have_value("IDEAS")
