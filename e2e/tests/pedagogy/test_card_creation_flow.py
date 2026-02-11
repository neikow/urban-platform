from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from core.models import User
from e2e.utils import login_user


def test_pedagogy_card_creation_flow(
    page: Page,
    e2e_wagtail_admin_user: User,
    email: str,
    password: str,
    mock_image,
    setup_wagtail_pages,
    live_server: LiveServer,
):
    TEST_TITLE = "TEST_TITLE"
    TEST_DESCRIPTION = "TEST_DESCRIPTION"
    TEST_CONTENT = "TEST_CONTENT"
    TEST_URL = "https://youtube.com"

    login_user(
        page=page,
        live_server=live_server,
        email=email,
        password=password,
    )
    page.goto(live_server.url + "/admin/")

    page.get_by_role("button", name="Fiches Pédagogiques").click()
    page.get_by_role("link", name="Ajouter").click()
    page.get_by_role("textbox", name="Titre*").click()
    page.get_by_role("textbox", name="Titre*").fill(TEST_TITLE)
    page.get_by_role("textbox", name="Description de la fiche pé").fill(TEST_DESCRIPTION)
    page.get_by_role("button", name="Choisir une image").click()
    page.get_by_role("img", name=mock_image.title).click()
    page.get_by_role("button", name="Ajouter un(e) Ressource").click()
    page.get_by_role("textbox", name="URL externe").fill(TEST_URL)
    page.get_by_role("button", name="Insérer un bloc").click()
    page.get_by_text("Texte", exact=True).click()

    editor = page.locator(".public-DraftStyleDefault-block")
    editor.click()
    editor.type(TEST_CONTENT)

    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()
    page.get_by_role("button", name=f"Plus d’options pour « {TEST_TITLE} »").click()
    page.get_by_role("link", name="Visualiser la version publiée").first.click()

    expect(page.locator("h1", has_text=TEST_TITLE)).to_be_visible()
    expect(page.get_by_text(TEST_DESCRIPTION)).to_be_visible()
    expect(page.locator(f"img[alt='{TEST_TITLE}']")).to_be_visible()
    expect(page.locator(f"a[href='{TEST_URL}']").first).to_be_visible()
    expect(page.locator("p", has_text=TEST_CONTENT)).to_be_visible(timeout=60000)
