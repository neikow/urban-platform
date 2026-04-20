import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect
from django.utils.translation import gettext as _

from e2e.utils import login_user


@pytest.fixture
def deletion_test_user_credentials():
    """Return credentials for the deletion test user created by e2e setup script."""
    return {
        "email": "e2e.delete.test@email.com",
        "password": "DeleteTest123",
    }


@pytest.mark.e2e
def test_login_flow(page: Page, base_url: str, user_email: str, user_password: str):
    """Test that a user can log in through the UI."""
    login_user(
        page=page,
        base_url=base_url,
        email=user_email,
        password=user_password,
    )

    expect(page).to_have_url(base_url + "/")


@pytest.mark.e2e
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

    registration_form.locator("button[type='submit']", has_text=_("Sign up")).click()

    # Wait for consent page
    expect(page).to_have_url(
        re.compile(f"^{re.escape(base_url + reverse('code_of_conduct_consent'))}")
    )

    # Scroll to consent checkbox and accept
    page.locator("#page-content-end").scroll_into_view_if_needed()
    page.locator("input[name='consent']").click()

    # Click accept button and wait for redirect to me page
    page.get_by_role("button", name=_("Accept and continue")).click()
    expect(page).to_have_url(base_url + reverse("me"))


@pytest.mark.e2e
def test_account_deletion_flow(page: Page, base_url: str, deletion_test_user_credentials: dict):
    """Test that a user can delete their account through the UI.

    Note: This test uses a user created by the e2e setup script.
    Run 'python scripts/e2e.py setup' or 'python scripts/e2e.py populate' to recreate the user.
    """
    email = deletion_test_user_credentials["email"]
    password = deletion_test_user_credentials["password"]

    # Login as the deletion test user
    login_user(page=page, base_url=base_url, email=email, password=password)

    # Navigate to profile edit page
    page.goto(base_url + reverse("profile_edit"))

    # Click on "Supprimer mon compte" button
    page.get_by_role("link", name=_("Delete my account")).click()

    # Should be on account deletion page
    expect(page).to_have_url(base_url + reverse("account_delete"))

    # Verify warning messages are displayed
    expect(page.locator(f"text={_('Warning: Irreversible action')}")).to_be_visible()
    expect(page.locator(f"text={_('Delete my account')}")).to_be_visible()

    # Fill in password confirmation (use placeholder to distinguish from login modal password)
    page.get_by_placeholder("Entrez votre mot de passe pour confirmer").fill(password)

    # Check the confirmation checkbox
    page.locator("input[name='confirm']").click()

    # Submit the deletion form
    page.get_by_role("button", name="Supprimer définitivement mon compte").click()

    # Should redirect to home page after deletion
    expect(page).to_have_url(base_url + "/")

    # Try to login again with deleted account credentials - should fail
    page.goto(base_url)
    page.get_by_role("button", name=_("Log in")).first.click()

    page.locator("input[name='modal-email']").fill(email)
    page.locator("input[name='modal-password']").fill(password)
    page.locator("#login_modal button[type='submit']", has_text=_("Log in")).click()

    # Should show error message (account is deleted/deactivated)
    expect(page.locator("#login-error")).to_be_visible()
