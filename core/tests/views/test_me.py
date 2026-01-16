from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class MeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="testuser@example.com", password="Password123", first_name="Test", last_name="User")
        self.me_url = reverse("me")

    def test_me_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com"
        })

    def test_me_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
