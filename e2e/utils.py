"""
E2E Test Utilities.

Helper functions for E2E tests that run against a real Django server.
"""

from django.urls import reverse
from playwright.sync_api import Page
from django.utils.translation import gettext as _


def login_user(page: Page, base_url: str, email: str, password: str) -> None:
    """
    Log in a user through the UI.

    Args:
        page: Playwright page object
        base_url: Base URL of the E2E server
        email: User's email address
        password: User's password
    """
    page.goto(base_url)
    page.get_by_role("button", name=_("Log in")).click()

    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)

    with page.expect_response(
        lambda res: res.url.endswith(reverse("login")) and res.request.method == "POST"
    ) as response_info:
        page.locator("#login_modal button[type='submit']", has_text=_("Log in")).click()

    response = response_info.value
    assert response.ok, f"Login failed with status {response.status}"

    # Wait for modal to close (indicates successful login)
    page.locator("#login_modal").wait_for(state="hidden", timeout=5000)


def logout_user(page: Page, base_url: str) -> None:
    """
    Log out the current user through the UI.

    Args:
        page: Playwright page object
        base_url: Base URL of the E2E server
    """
    page.goto(base_url + reverse("logout"))
    page.wait_for_url(base_url + "/")
