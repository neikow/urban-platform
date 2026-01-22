from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

VALID_REQUEST = {
    "email": "testuser@example.com",
    "password": "Password123",
    "confirm_password": "Password123",
    "first_name": "Test",
    "last_name": "User",
    "postal_code": "13001",
    "accept_terms": True,
}

User = get_user_model()


class RegisterViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.register_url = reverse("register")

    def test_register_success(self) -> None:
        response = self.client.post(self.register_url, VALID_REQUEST)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,  # type: ignore[attr-defined]
            reverse("me"),
        )
        self.assertTrue(User.objects.filter(email="testuser@example.com").exists())

    def test_register_email_already_used(self) -> None:
        User.objects.create_user(email="testuser@example.com", password="Password123")
        response = self.client.post(self.register_url, VALID_REQUEST)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email déjà utilisé.")

    def test_register_password_mismatch(self) -> None:
        response = self.client.post(
            self.register_url,
            {
                "email": "testuser@example.com",
                "password": "Password123",
                "confirm_password": "Password321",
                "first_name": "Test",
                "last_name": "User",
                "postal_code": "13001",
                "accept_terms": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Les mots de passe ne correspondent pas.")

    def test_register_password_strength(self) -> None:
        response = self.client.post(
            self.register_url,
            {
                "email": "testuser@example.com",
                "password": "weak",
                "confirm_password": "weak",
                "first_name": "Test",
                "last_name": "User",
                "postal_code": "13001",
                "accept_terms": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Le mot de passe doit contenir au moins 8 caractères, une lettre majuscule et un chiffre.",
        )

    def test_register_accept_terms_required(self) -> None:
        response = self.client.post(
            self.register_url,
            {
                "email": "testuser@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
                "first_name": "Test",
                "last_name": "User",
                "postal_code": "13001",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Vous devez accepter la charte de bonne conduite et les conditions d&#x27;utilisation pour vous inscrire.",
        )

    def test_register_user_logged_in_after_success(self) -> None:
        """Test that user is automatically logged in after successful registration."""
        response = self.client.post(self.register_url, VALID_REQUEST)
        self.assertEqual(response.status_code, 302)

        # Check that user is logged in
        user = User.objects.get(email="testuser@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_register_user_data_saved_correctly(self) -> None:
        """Test that user data is saved correctly in the database."""
        self.client.post(self.register_url, VALID_REQUEST)

        user = User.objects.get(email="testuser@example.com")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.postal_code, "13001")
        self.assertTrue(user.check_password("Password123"))

    def test_register_missing_required_fields(self) -> None:
        """Test registration with missing required fields."""
        response = self.client.post(
            self.register_url,
            {
                "email": "testuser@example.com",
                # Missing all other fields
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="testuser@example.com").exists())

    def test_register_invalid_email_format(self) -> None:
        """Test registration with invalid email format."""
        response = self.client.post(
            self.register_url,
            {
                "email": "not-an-email",
                "password": "Password123",
                "confirm_password": "Password123",
                "first_name": "Test",
                "last_name": "User",
                "postal_code": "13001",
                "accept_terms": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="not-an-email").exists())

    def test_register_password_without_uppercase(self) -> None:
        """Test that password without uppercase letter is rejected."""
        response = self.client.post(
            self.register_url,
            {
                "email": "testuser@example.com",
                "password": "password123",
                "confirm_password": "password123",
                "first_name": "Test",
                "last_name": "User",
                "postal_code": "13001",
                "accept_terms": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "majuscule")

    def test_register_password_without_digit(self) -> None:
        """Test that password without digit is rejected."""
        response = self.client.post(
            self.register_url,
            {
                "email": "testuser@example.com",
                "password": "PasswordABC",
                "confirm_password": "PasswordABC",
                "first_name": "Test",
                "last_name": "User",
                "postal_code": "13001",
                "accept_terms": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "chiffre")

    def test_register_renders_correct_template(self) -> None:
        """Test that registration page renders the correct template."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/register.html")
