import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect

from e2e.utils import login_user


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

    registration_form.locator("button[type='submit']", has_text="S'inscrire").click()

    # Wait for consent page
    expect(page).to_have_url(
        re.compile(f"^{re.escape(base_url + reverse('code_of_conduct_consent'))}")
    )

    # Scroll to consent checkbox and accept
    page.locator("#page-content-end").scroll_into_view_if_needed()
    page.locator("input[name='consent']").click()

    # Click accept button and wait for redirect to me page
    page.get_by_role("button", name="Accepter et continuer").click()
    expect(page).to_have_url(base_url + reverse("me"))


@pytest.mark.e2e
def test_account_deletion_flow(page: Page, base_url: str, django_user_model):
    """Test that a user can delete their account and data is anonymized."""
    import uuid
    from publications.models import FormResponse, ProjectPage
    from core.models import User

    unique_email = f"e2e.delete.{uuid.uuid4().hex[:8]}@email.com"
    test_user = django_user_model.objects.create_user(
        email=unique_email,
        password="Password123",
        first_name="ToDelete",
        last_name="User",
        postal_code="13001",
    )
    user_id = test_user.pk
    user_email = test_user.email

    # Create test data: a vote on a project
    project = ProjectPage.objects.live().first()
    vote = None
    if project:
        vote = FormResponse.objects.create(
            user=test_user,
            project=project,
            choice="FAVORABLE",
            comment="This is my test comment",
            anonymize=False,
        )

    login_user(page=page, base_url=base_url, email=unique_email, password="Password123")

    page.goto(base_url + reverse("profile_edit"))
    page.get_by_role("link", name="Supprimer mon compte").click()

    expect(page).to_have_url(base_url + reverse("account_delete"))
    expect(page.locator("text=Action irréversible")).to_be_visible()
    expect(page.locator("text=Supprimer mon compte")).to_be_visible()

    page.locator("input[name='password']").fill("Password123")
    page.locator("input[name='confirm']").click()
    page.get_by_role("button", name="Supprimer définitivement mon compte").click()

    expect(page).to_have_url(base_url + "/")
    expect(page.locator(f"text={user_email}")).to_be_visible()
    expect(page.locator("text=supprimé avec succès")).to_be_visible()

    # Verify user is soft-deleted
    assert not User.objects.filter(pk=user_id).exists()
    assert not User.objects.filter(email=unique_email).exists()
    deleted_user = User.objects.with_deleted().get(pk=user_id)
    assert deleted_user.is_deleted is True
    assert deleted_user.deleted_at is not None

    assert deleted_user.first_name == "Utilisateur"
    assert deleted_user.last_name == "Supprimé"
    assert deleted_user.email == f"deleted.{deleted_user.uuid}@deleted.local"
    assert deleted_user.phone_number == ""
    assert deleted_user.is_active is False

    # Verify vote still exists and points to soft-deleted user
    if vote:
        vote.refresh_from_db()
        assert vote.user.pk == deleted_user.pk
        assert vote.user.is_deleted is True

    # Try to login again with deleted account credentials - should fail
    page.goto(base_url)
    page.get_by_role("button", name="Se connecter").click()

    page.locator("input[name='email']").fill(unique_email)
    page.locator("input[name='password']").fill("Password123")
    page.locator("#login_modal button[type='submit']", has_text="Se connecter").click()

    # Should show error message
    expect(page.locator("#login-error")).to_be_visible()
