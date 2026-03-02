"""
E2E Test Utilities.

Helper functions for E2E tests that run against a real Django server.
"""

from django.urls import reverse
from playwright.sync_api import Page


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
    page.get_by_role("button", name="Se connecter").click()

    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("#login_modal button[type='submit']", has_text="Se connecter").click()
    page.wait_for_url(base_url + reverse("me"))


def logout_user(page: Page, base_url: str) -> None:
    """
    Log out the current user through the UI.

    Args:
        page: Playwright page object
        base_url: Base URL of the E2E server
    """
    page.goto(base_url + reverse("logout"))
    page.wait_for_url(base_url + "/")
