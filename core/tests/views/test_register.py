from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

VALID_REQUEST = {
    "email": "testuser@example.com",
    "password": "Password123",
    "confirm_password": "Password123",
    "first_name": "Test",
    "last_name": "User"
}

User = get_user_model()

class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")

    def test_register_success(self):
        response = self.client.post(self.register_url, VALID_REQUEST)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("me"))
        self.assertTrue(User.objects.filter(email="testuser@example.com").exists())

    def test_register_email_already_used(self):
        User.objects.create_user(email="testuser@example.com", password="Password123")
        response = self.client.post(self.register_url, VALID_REQUEST)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email déjà utilisé.")

    def test_register_password_mismatch(self):
        response = self.client.post(self.register_url, {
            "email": "testuser@example.com",
            "password": "Password123",
            "confirm_password": "Password321",
            "first_name": "Test",
            "last_name": "User"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Les mots de passe ne correspondent pas.")

    def test_register_password_strength(self):
        response = self.client.post(self.register_url, {
            "email": "testuser@example.com",
            "password": "weak",
            "confirm_password": "weak",
            "first_name": "Test",
            "last_name": "User"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le mot de passe doit contenir au moins 8 caractères, une lettre majuscule et un chiffre.")
