import pytest
from playwright.sync_api import Page, expect

from e2e.utils import login_user


@pytest.mark.e2e
def test_moderator_can_access_docs(
    page: Page,
    base_url: str,
    moderator_email: str,
    moderator_password: str,
):
    """A moderator (admin access via Moderator group) can reach the protected docs."""
    login_user(
        page=page,
        base_url=base_url,
        email=moderator_email,
        password=moderator_password,
    )

    response = page.goto(base_url + "/admin/docs/")

    assert response is not None
    assert response.ok, f"Docs access failed with status {response.status}"
    expect(page).to_have_url(base_url + "/admin/docs/")


@pytest.mark.e2e
def test_regular_user_cannot_access_docs(
    page: Page,
    base_url: str,
    user_email: str,
    user_password: str,
):
    """A regular user without admin access is redirected away from the docs."""
    login_user(
        page=page,
        base_url=base_url,
        email=user_email,
        password=user_password,
    )

    page.goto(base_url + "/admin/docs/")

    expect(page).not_to_have_url(base_url + "/admin/docs/")
