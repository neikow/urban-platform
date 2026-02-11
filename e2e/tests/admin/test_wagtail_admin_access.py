from django.urls import reverse
from pytest_django.live_server_helper import LiveServer
from playwright.sync_api import Page, expect

from e2e.utils import login_user


def test_wagtail_admin_access(
    page: Page,
    e2e_wagtail_admin_user,
    email: str,
    password: str,
    settings,
    live_server: LiveServer,
    setup_wagtail_pages,
    setup_legal_pages,
):
    login_user(
        page=page,
        live_server=live_server,
        email=email,
        password=password,
    )
    page.goto(live_server.url + "/admin/")

    expect(page).to_have_url(
        live_server.url + "/admin/",
    )
    expect(page.locator("header h1", has_text=settings.WEBSITE_NAME)).to_be_visible()
