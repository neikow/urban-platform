from django.http import HttpResponse
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class MeViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
        )
        self.me_url = reverse("me")

    def test_me_authenticated_displays_profile(self) -> None:
        """Test that authenticated user can view their profile page."""
        self.client.force_login(self.user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/profile.html")
        self.assertContains(response, "Mon profil")
        self.assertContains(response, "Test")
        self.assertContains(response, "User")
        self.assertContains(response, "testuser@example.com")

    def test_me_unauthenticated_redirects_to_login(self) -> None:
        """Test that unauthenticated user is redirected to login."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore[attr-defined]

    def test_me_displays_all_user_fields(self) -> None:
        """Test that all user information fields are displayed."""
        self.user.phone_number = "0612345678"
        self.user.newsletter_subscription = True
        self.user.postal_code = "13001"
        self.user.save()

        self.client.force_login(self.user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0612345678")
        self.assertContains(response, "13001")
        self.assertContains(response, "Abonné")  # Newsletter subscription badge

    def test_me_displays_role_badge(self) -> None:
        """Test that user role is displayed with correct badge."""
        self.client.force_login(self.user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Citoyen")  # Default role is CITIZEN

    def test_me_displays_verified_status(self) -> None:
        """Test that email verification status is displayed."""
        self.client.force_login(self.user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Non vérifié")  # Default is not verified

        # Update user to verified
        self.user.is_verified = True
        self.user.save()
        response = self.client.get(self.me_url)

        self.assertContains(response, "Vérifié")
