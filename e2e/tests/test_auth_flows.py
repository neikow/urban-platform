from django.urls import reverse
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from e2e.utils import login_user


def test_login_flow(
    page: Page, e2e_default_user, email, password, live_server: LiveServer, setup_wagtail_pages
):
    login_user(
        page=page,
        live_server=live_server,
        email=email,
        password=password,
    )

    expect(page).to_have_url(live_server.url + reverse("me"))


def test_registration_flow(
    page: Page, live_server: LiveServer, setup_wagtail_pages, setup_legal_pages
):
    page.goto(live_server.url + reverse("register"))
    page.get_by_role("button", name="S'inscrire").click()

    registration_form = page.locator("#registration-form")

    registration_form.locator("input[name='email']").fill(
        "e2e@email.com",
    )
    registration_form.locator("input[name='first_name']").fill("E2E")
    registration_form.locator("input[name='last_name']").fill("Test")
    registration_form.locator("input[name='postal_code']").fill(
        "13007",
    )
    registration_form.locator("input[name='password']").fill(
        "Password123",
    )
    registration_form.locator("input[name='confirm_password']").fill(
        "Password123",
    )
    registration_form.locator("input[name='accept_terms']").click()

    registration_form.locator("button[type='submit']", has_text="S'inscrire").click()

    expect(page).to_have_url(live_server.url + reverse("code_of_conduct_consent"))

    page.locator("#page-content-end").scroll_into_view_if_needed()

    page.locator("input[name='consent']").click()

    page.get_by_role("button", name="Accepter et continuer").click()

    expect(page).to_have_url(live_server.url + reverse("me"))
