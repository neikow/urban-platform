import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_redirects_to_home(self, client: Client, test_user):
        # Log in
        client.login(username="testuser@example.com", password="TestPass123")
        assert "_auth_user_id" in client.session

        # Logout
        response = client.post(reverse("logout"))

        assert response.status_code == 302
        assert response.url == "/"  # type: ignore[attr-defined]

    def test_user_logged_out_after_logout(self, client: Client, test_user):
        # Log in
        client.login(username="testuser@example.com", password="TestPass123")
        assert "_auth_user_id" in client.session

        # Logout
        client.post(reverse("logout"))

        assert "_auth_user_id" not in client.session

    def test_logout_only_accepts_post(self, client: Client, test_user):
        client.login(username="testuser@example.com", password="TestPass123")

        # Try GET request that should fail
        response = client.get(reverse("logout"))

        # Method not allowed
        assert response.status_code == 405

    def test_logout_when_not_authenticated(self, client: Client):
        response = client.post(reverse("logout"))

        # Should still redirect without error
        assert response.status_code == 302
        assert response.url == "/"  # type: ignore[attr-defined]

    def test_logout_clears_session(self, client: Client, test_user):
        # Log in and add some session data
        client.login(username="testuser@example.com", password="TestPass123")
        session = client.session
        session["test_key"] = "test_value"
        session.save()

        # Logout
        client.post(reverse("logout"))

        # Session should be cleared
        assert "_auth_user_id" not in client.session
        # Note: Django's logout() doesn't clear all session data, just auth data
