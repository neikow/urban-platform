from django.urls import reverse
from playwright.sync_api import Page, expect

from e2e.utils import login_user


def test_login_flow(page: Page, base_url: str, user_email: str, user_password: str):
    """Test that a user can log in through the UI."""
    login_user(
        page=page,
        base_url=base_url,
        email=user_email,
        password=user_password,
    )

    expect(page).to_have_url(base_url + reverse("me"))


def test_registration_flow(page: Page, base_url: str):
    """Test that a new user can register through the UI."""
    import uuid

    # Use unique email to avoid conflicts with persistent database
    unique_email = f"e2e.register.{uuid.uuid4().hex[:8]}@email.com"

    page.goto(base_url + reverse("register"))
    page.get_by_role("button", name="S'inscrire").click()

    registration_form = page.locator("#registration-form")

    registration_form.locator("input[name='email']").fill(unique_email)
    registration_form.locator("input[name='first_name']").fill("E2E")
    registration_form.locator("input[name='last_name']").fill("Test")
    registration_form.locator("input[name='postal_code']").fill("13007")
    registration_form.locator("input[name='password']").fill("Password123")
    registration_form.locator("input[name='confirm_password']").fill("Password123")
    registration_form.locator("input[name='accept_terms']").click()

    registration_form.locator("button[type='submit']", has_text="S'inscrire").click()

    # Wait for consent page
    page.wait_for_url(base_url + reverse("code_of_conduct_consent"))
    expect(page).to_have_url(base_url + reverse("code_of_conduct_consent"))

    # Scroll to consent checkbox and accept
    page.locator("#page-content-end").scroll_into_view_if_needed()
    page.locator("input[name='consent']").click()

    # Click accept button and wait for redirect to me page
    page.get_by_role("button", name="Accepter et continuer").click()
    page.wait_for_url(base_url + reverse("me"))
    expect(page).to_have_url(base_url + reverse("me"))
