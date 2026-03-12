import uuid

import pytest
from playwright.sync_api import Page, expect
from django.utils.translation import gettext as _

from e2e.utils import login_user


@pytest.mark.e2e
def test_about_website_page_edition(
    page: Page,
    base_url: str,
    admin_email: str,
    admin_password: str,
):
    unique_id = uuid.uuid4().hex[:8]
    TEST_CONTENT = f"TEST_CONTENT_{unique_id}"

    login_user(
        page=page,
        base_url=base_url,
        email=admin_email,
        password=admin_password,
    )
    page.goto(base_url + "/admin/")

    page.get_by_role("button", name="À propos").click()
    page.get_by_label("À propos").get_by_role("link", name="La plateforme").click()

    editor = page.locator(".public-DraftStyleDefault-block")
    editor.click()
    page.keyboard.type(TEST_CONTENT)
    page.wait_for_timeout(300)

    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()

    page.goto(base_url + "/a-propos/la-plateforme/")

    expect(page.get_by_text(TEST_CONTENT)).to_be_visible()


@pytest.mark.e2e
def test_about_commission_page_edition(
    page: Page,
    base_url: str,
    admin_email: str,
    admin_password: str,
):
    unique_id = uuid.uuid4().hex[:8]
    TEST_CONTENT = f"TEST_CONTENT_{unique_id}"

    login_user(
        page=page,
        base_url=base_url,
        email=admin_email,
        password=admin_password,
    )
    page.goto(base_url + "/admin/")

    page.get_by_role("button", name="À propos").click()
    page.get_by_label("À propos").get_by_role("link", name="La commission d'urbanisme").click()

    editor = page.locator(".public-DraftStyleDefault-block")
    editor.click()
    page.keyboard.type(TEST_CONTENT)
    page.wait_for_timeout(300)

    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()

    page.goto(base_url + "/a-propos/commission-urbanisme/")

    expect(page.get_by_text(TEST_CONTENT)).to_be_visible()


@pytest.mark.e2e
def test_about_dev_team_page_edition(
    page: Page,
    base_url: str,
    admin_email: str,
    admin_password: str,
):
    unique_id = uuid.uuid4().hex[:8]
    TEST_CONTENT = f"TEST_CONTENT_{unique_id}"

    login_user(
        page=page,
        base_url=base_url,
        email=admin_email,
        password=admin_password,
    )
    page.goto(base_url + "/admin/")

    page.get_by_role("button", name="À propos").click()
    page.get_by_label("À propos").get_by_role("link", name="L'équipe de développement").click()

    editor = page.locator(".public-DraftStyleDefault-block")
    editor.click()
    page.keyboard.type(TEST_CONTENT)
    page.wait_for_timeout(300)

    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()

    page.goto(base_url + "/a-propos/equipe-de-developpement/")

    expect(page.get_by_text(TEST_CONTENT)).to_be_visible()
