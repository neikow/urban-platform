from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from core.models import User
from e2e.utils import login_user


def test_pedagogy_card_index_page_edition(
    page: Page, e2e_wagtail_admin_user: User, email: str, password: str, live_server: LiveServer
):
    login_user(
        page=page,
        live_server=live_server,
        email=email,
        password=password,
    )
    page.goto(live_server.url + "/admin/")

    page.get_by_role("button", name="Fiches Pédagogiques").click()
    page.get_by_label("Fiches Pédagogiques").get_by_role("link", name="Page d'accueil").click()
    page.get_by_role("textbox", name="Introduction de la page").fill("TEST_CONTENT")
    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()
    page.get_by_role("link", name="Fiches pédagogiques", exact=True).click()
    page.get_by_role("button", name="Actions", exact=True).click()
    page.get_by_role("button", name="Actions", exact=True).press("Escape")
    page.get_by_role("tab", name="Promotion").click()
    page.get_by_role("tab", name="Contenu").click()

    page.goto(live_server.url + "/fiches-pedagogiques/")

    expect(page.get_by_text("TEST_CONTENT")).to_be_visible()
