from django.urls import reverse
from playwright.sync_api import Page
from pytest_django.live_server_helper import LiveServer


def login_user(page: Page, live_server: LiveServer, email: str, password: str) -> None:
    page.goto(live_server.url)
    page.get_by_role("button", name="Se connecter").click()

    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("#login_modal button[type='submit']", has_text="Se connecter").click()
    page.wait_for_url(live_server.url + reverse("me"))
