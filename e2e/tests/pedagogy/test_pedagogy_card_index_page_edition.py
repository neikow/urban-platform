import uuid

from playwright.sync_api import Page, expect

from e2e.utils import login_user


def test_pedagogy_card_index_page_edition(
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

    page.get_by_role("button", name="Fiches Pédagogiques").click()
    page.get_by_label("Fiches Pédagogiques").get_by_role("link", name="Page d'accueil").click()
    page.get_by_role("textbox", name="Introduction de la page").fill(TEST_CONTENT)
    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()
    page.get_by_role("link", name="Fiches pédagogiques", exact=True).click()
    page.get_by_role("button", name="Actions", exact=True).click()
    page.get_by_role("button", name="Actions", exact=True).press("Escape")
    page.get_by_role("tab", name="Promotion").click()
    page.get_by_role("tab", name="Contenu").click()

    page.goto(base_url + "/fiches-pedagogiques/")

    expect(page.get_by_text(TEST_CONTENT)).to_be_visible()
