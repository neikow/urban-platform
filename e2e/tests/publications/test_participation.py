import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Page, expect

from e2e.utils import login_user

VOTE_PROJECT_PATH = "/actualites/projet-vote/"
IDEAS_PROJECT_PATH = "/actualites/projet-idees/"


def choose_vote(page: Page, choice: str) -> None:
    page.locator(f"label.vote-choice-btn:has(input[value='{choice}'])").click()


@pytest.mark.e2e
def test_vote_change_and_remove(page: Page, base_url: str, voter_email: str, voter_password: str):
    login_user(page=page, base_url=base_url, email=voter_email, password=voter_password)
    page.goto(base_url + VOTE_PROJECT_PATH)

    choose_vote(page, "FAVORABLE")
    page.locator("#vote-comment").fill("Bonne idée pour le quartier")
    page.locator("#vote-submit-btn").click()

    expect(page.locator("#vote-results-container")).to_be_visible()
    expect(page.locator("#user-vote-choice")).to_have_text(_("Favorable"))
    expect(page.locator("#user-vote-comment")).to_have_text("Bonne idée pour le quartier")

    # The vote is kept across reloads.
    page.reload()
    expect(page.locator("#user-vote-choice")).to_have_text(_("Favorable"))

    page.locator("#change-vote-btn").click()
    choose_vote(page, "RATHER_UNFAVORABLE")
    page.locator("#vote-submit-btn").click()
    expect(page.locator("#user-vote-choice")).to_have_text(_("Rather Unfavorable"))

    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("#remove-vote-btn").click()
    expect(page.locator("#vote-form-container")).to_be_visible()
    expect(page.locator("#vote-results-container")).to_be_hidden()


@pytest.mark.e2e
def test_submit_edit_and_remove_idea(
    page: Page, base_url: str, voter_email: str, voter_password: str
):
    login_user(page=page, base_url=base_url, email=voter_email, password=voter_password)
    page.goto(base_url + IDEAS_PROJECT_PATH)

    page.locator("#ideas-description").fill("Planter des arbres le long de la rue")
    page.locator("#ideas-submit-btn").click()

    expect(page.locator("#ideas-result-container")).to_be_visible()
    expect(page.locator("#ideas-result-text")).to_have_text("Planter des arbres le long de la rue")

    page.locator("#ideas-change-btn").click()
    page.locator("#ideas-description").fill("Planter des arbres et ajouter des bancs")
    page.locator("#ideas-submit-btn").click()
    expect(page.locator("#ideas-result-text")).to_have_text(
        "Planter des arbres et ajouter des bancs"
    )

    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("#ideas-remove-btn").click()
    expect(page.locator("#ideas-form-container")).to_be_visible()


@pytest.mark.e2e
def test_anonymous_visitor_is_asked_to_log_in(page: Page, base_url: str):
    page.goto(base_url + VOTE_PROJECT_PATH)

    expect(page.locator("#vote-login-prompt")).to_be_visible()
    expect(page.locator("#vote-form")).to_have_count(0)


@pytest.mark.e2e
def test_unverified_user_is_asked_to_verify_email(
    page: Page, base_url: str, user_email: str, user_password: str
):
    # The default e2e user never verified their email address.
    login_user(page=page, base_url=base_url, email=user_email, password=user_password)
    page.goto(base_url + VOTE_PROJECT_PATH)

    expect(page.get_by_role("button", name=_("Resend the verification link"))).to_be_visible()
    expect(page.locator("#vote-form")).to_have_count(0)
