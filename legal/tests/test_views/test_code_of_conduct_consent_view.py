from unittest.mock import patch, MagicMock

import pytest
from django.test import Client
from django.contrib.auth import get_user_model

from legal.views import CodeOfConductConsentView

User = get_user_model()


@pytest.fixture
def authenticated_client(client: Client, django_user_model):
    user = django_user_model.objects.create_user(email="test@example.com", password="testpass123")
    client.force_login(user)
    return client, user


@pytest.mark.django_db
class TestCodeOfConductConsentViewGet:
    def test_unauthenticated_redirects_to_login(self, client: Client):
        response = client.get("/user/code-of-conduct-consent/")
        assert response.status_code == 302
        assert "/login" in response.url  # type: ignore[attr-defined]

    @patch("legal.views.has_valid_code_of_conduct_consent", return_value=True)
    def test_with_valid_consent_redirects_to_me(self, mock_consent, authenticated_client):
        client, user = authenticated_client
        response = client.get("/user/code-of-conduct-consent/")
        assert response.status_code == 302
        assert response.url == "/auth/me/"

    @patch("legal.views.has_valid_code_of_conduct_consent", return_value=False)
    def test_without_consent_shows_form(self, mock_consent, authenticated_client):
        client, user = authenticated_client
        response = client.get("/user/code-of-conduct-consent/")
        assert response.status_code == 200
        assert "form" in response.context


@pytest.mark.django_db
class TestCodeOfConductConsentViewPost:
    @patch("legal.views.has_valid_code_of_conduct_consent", return_value=False)
    @patch("legal.views.create_code_of_conduct_consent_record")
    def test_valid_form_creates_consent_and_redirects(
        self, mock_create, mock_consent, authenticated_client
    ):
        client, user = authenticated_client
        response = client.post("/user/code-of-conduct-consent/", {"consent": True})

        assert response.status_code == 302
        assert response.url == "/auth/me/"
        mock_create.assert_called_once()

    @patch("legal.views.has_valid_code_of_conduct_consent", return_value=False)
    def test_invalid_form_shows_errors(self, mock_consent, authenticated_client):
        client, user = authenticated_client
        response = client.post("/user/code-of-conduct-consent/", {})

        assert response.status_code == 200
        assert response.context["form"].errors


class TestCodeOfConductConsentViewContext:
    @patch("legal.views.has_valid_code_of_conduct_consent", return_value=False)
    @patch("legal.views.CodeOfConductPage.objects.live")
    def test_context_includes_code_of_conduct_content(
        self, mock_live_code_of_conduct_page, mock_consent, authenticated_client
    ):
        mock_page = MagicMock()
        mock_page.content = "Test Code of Conduct Content"
        mock_live_code_of_conduct_page.return_value.first.return_value = mock_page

        client, user = authenticated_client
        response = client.get("/user/code-of-conduct-consent/")

        assert response.status_code == 200
        assert response.context["content"] == "Test Code of Conduct Content"
