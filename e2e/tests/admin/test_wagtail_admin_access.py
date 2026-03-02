from playwright.sync_api import Page, expect

from e2e.utils import login_user


def test_wagtail_admin_access(
    page: Page,
    base_url: str,
    admin_email: str,
    admin_password: str,
):
    """Test that an admin user can access the Wagtail admin panel."""
    login_user(
        page=page,
        base_url=base_url,
        email=admin_email,
        password=admin_password,
    )
    page.goto(base_url + "/admin/")

    expect(page).to_have_url(base_url + "/admin/")
    expect(page.locator("header h1")).to_be_visible()
