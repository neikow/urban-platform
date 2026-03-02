import uuid

from playwright.sync_api import Page, expect

from e2e.utils import login_user


def test_pedagogy_card_creation_flow(
    page: Page,
    base_url: str,
    admin_email: str,
    admin_password: str,
):
    unique_id = uuid.uuid4().hex[:8]
    TEST_TITLE = f"TEST_TITLE_{unique_id}"
    TEST_DESCRIPTION = f"TEST_DESCRIPTION_{unique_id}"
    TEST_CONTENT = f"TEST_CONTENT_{unique_id}"
    TEST_URL = "https://youtube.com"

    login_user(
        page=page,
        base_url=base_url,
        email=admin_email,
        password=admin_password,
    )
    page.goto(base_url + "/admin/")

    page.get_by_role("button", name="Fiches Pédagogiques").click()
    page.get_by_role("link", name="Ajouter").click()
    page.get_by_role("textbox", name="Titre*").click()
    page.get_by_role("textbox", name="Titre*").fill(TEST_TITLE)
    page.get_by_role("textbox", name="Description de la fiche pé").fill(TEST_DESCRIPTION)
    page.get_by_role("button", name="Choisir une image").click()
    # Wait a moment for modal to appear
    page.wait_for_timeout(500)

    # Try to find and click on any image in the chooser
    images = page.locator("img[role='button']")
    if images.count() > 0:
        images.first.click()
    else:
        # If no images, close the modal
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

    page.get_by_role("button", name="Ajouter un(e) Ressource").click()
    page.get_by_role("textbox", name="URL externe").fill(TEST_URL)
    page.get_by_role("button", name="Insérer un bloc").click()
    page.get_by_text("Texte", exact=True).click()

    editor = page.locator(".public-DraftStyleDefault-block")
    editor.click()
    page.keyboard.type(TEST_CONTENT)
    page.wait_for_timeout(300)

    page.get_by_role("button", name="Plus d'actions").click()
    page.get_by_role("button", name="Publier").click()

    page.get_by_role("link", name="Visualiser la version publiée").first.click()

    expect(page.locator("h1", has_text=TEST_TITLE)).to_be_visible()
    expect(page.get_by_text(TEST_DESCRIPTION)).to_be_visible()
    expect(page.locator(f"a[href='{TEST_URL}']").first).to_be_visible()
    expect(page.locator("p", has_text=TEST_CONTENT)).to_be_visible(timeout=60000)
