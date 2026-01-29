from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class ProfileEditViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
            postal_code="13001",
        )
        self.profile_edit_url = reverse("profile_edit")

    def test_profile_edit_unauthenticated_redirects(self) -> None:
        response = self.client.get(self.profile_edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore[attr-defined]

    def test_profile_edit_displays_form(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(self.profile_edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/profile_edit.html")
        self.assertContains(response, "Modifier mon profil")
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.user.first_name)

    def test_profile_edit_form_prepopulated(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(self.profile_edit_url)

        form = response.context["form"]
        self.assertEqual(form.initial["email"], self.user.email)
        self.assertEqual(form.initial["first_name"], self.user.first_name)
        self.assertEqual(form.initial["last_name"], self.user.last_name)
        self.assertEqual(form.initial["postal_code"], self.user.postal_code)

    def test_profile_update_success(self) -> None:
        self.client.force_login(self.user)

        data = {
            "email": "newemail@example.com",
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "postal_code": "13002",
            "phone_number": "0612345678",
            "newsletter_subscription": True,
        }

        response = self.client.post(self.profile_edit_url, data)

        self.assertRedirects(response, reverse("me"))

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "newemail@example.com")
        self.assertEqual(self.user.first_name, "NewFirst")
        self.assertEqual(self.user.last_name, "NewLast")
        self.assertEqual(self.user.postal_code, "13002")
        self.assertEqual(self.user.phone_number, "0612345678")
        self.assertTrue(self.user.newsletter_subscription)

    def test_email_change_marks_as_unverified(self) -> None:
        self.user.is_verified = True
        self.user.save()

        self.client.force_login(self.user)

        data = {
            "email": "newemail@example.com",
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "postal_code": self.user.postal_code,
        }

        self.client.post(self.profile_edit_url, data)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_email_no_change_keeps_verified_status(self) -> None:
        self.user.is_verified = True
        self.user.save()

        self.client.force_login(self.user)

        data = {
            "email": self.user.email,
            "first_name": "NewFirst",
            "last_name": self.user.last_name,
            "postal_code": self.user.postal_code,
        }

        self.client.post(self.profile_edit_url, data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_duplicate_email_validation(self) -> None:
        # Create another user
        User.objects.create_user(
            email="other@example.com",
            password="Password123",
            first_name="Other",
            last_name="User",
            postal_code="13003",
        )

        self.client.force_login(self.user)

        data = {
            "email": "other@example.com",
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "postal_code": self.user.postal_code,
        }

        response = self.client.post(self.profile_edit_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "email", "Cet email est déjà utilisé.")

    def test_invalid_postal_code_validation(self) -> None:
        self.client.force_login(self.user)

        data = {
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "postal_code": "ABC",
        }

        response = self.client.post(self.profile_edit_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "postal_code",
            "Le code postal doit contenir uniquement des chiffres.",
        )


class PasswordChangeViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="OldPassword123",
            first_name="Test",
            last_name="User",
            postal_code="13001",
        )
        self.password_change_url = reverse("password_change")

    def test_password_change_unauthenticated_redirects(self) -> None:
        response = self.client.get(self.password_change_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore[attr-defined]

    def test_password_change_success(self) -> None:
        self.client.force_login(self.user)

        data = {
            "current_password": "OldPassword123",
            "new_password": "NewPassword123",
            "confirm_password": "NewPassword123",
        }

        response = self.client.post(self.password_change_url, data, follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))  # type: ignore[attr-defined]

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123"))
        self.assertFalse(self.user.check_password("OldPassword123"))

    def test_password_change_wrong_current_password(self) -> None:
        self.client.force_login(self.user)

        data = {
            "current_password": "WrongPassword123",
            "new_password": "NewPassword123",
            "confirm_password": "NewPassword123",
        }

        response = self.client.post(self.password_change_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["password_form"],
            "current_password",
            "Le mot de passe actuel est incorrect.",
        )

    def test_password_change_mismatch(self) -> None:
        self.client.force_login(self.user)

        data = {
            "current_password": "OldPassword123",
            "new_password": "NewPassword123",
            "confirm_password": "DifferentPassword123",
        }

        response = self.client.post(self.password_change_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["password_form"],
            None,
            "Les nouveaux mots de passe ne correspondent pas.",
        )

    def test_password_change_weak_password(self) -> None:
        self.client.force_login(self.user)

        data = {
            "current_password": "OldPassword123",
            "new_password": "weak",
            "confirm_password": "weak",
        }

        response = self.client.post(self.password_change_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["password_form"],
            "new_password",
            "Le mot de passe doit contenir au moins 8 caractères, une lettre majuscule et un chiffre.",
        )
