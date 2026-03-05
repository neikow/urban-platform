import pytest
from django.contrib.auth import authenticate, get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from wagtail.models import Page

from core.views.account_delete import AccountDeleteForm
from publications.models import FormResponse, ProjectPage, PublicationIndexPage

User = get_user_model()


class AccountDeleteViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
            postal_code="13001",
        )
        self.account_delete_url = reverse("account_delete")

    def test_account_delete_unauthenticated_redirects(self) -> None:
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self.account_delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore[attr-defined]

    def test_account_delete_displays_form(self) -> None:
        """Test that the account deletion page displays correctly."""
        self.client.force_login(self.user)
        response = self.client.get(self.account_delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/account_delete.html")
        self.assertContains(response, "Supprimer mon compte")
        self.assertContains(response, "Action irréversible")

    def test_account_delete_requires_password(self) -> None:
        """Test that password is required to delete account."""
        self.client.force_login(self.user)

        data = {
            "password": "",
            "confirm": True,
        }

        response = self.client.post(self.account_delete_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Champ requis")
        # User should still exist
        self.assertTrue(User.objects.filter(email="testuser@example.com").exists())

    def test_account_delete_requires_confirmation(self) -> None:
        """Test that confirmation checkbox is required."""
        self.client.force_login(self.user)

        data = {
            "password": "Password123",
            "confirm": False,
        }

        response = self.client.post(self.account_delete_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="testuser@example.com").exists())

    def test_account_delete_wrong_password(self) -> None:
        """Test that wrong password prevents deletion."""
        self.client.force_login(self.user)

        data = {
            "password": "WrongPassword123",
            "confirm": True,
        }

        response = self.client.post(self.account_delete_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mot de passe incorrect")
        self.assertTrue(User.objects.filter(email="testuser@example.com").exists())

    def test_account_delete_success(self) -> None:
        """Test successful account deletion."""
        self.client.force_login(self.user)

        data = {
            "password": "Password123",
            "confirm": True,
        }

        response = self.client.post(self.account_delete_url, data)

        # Should redirect to home page
        self.assertRedirects(response, "/", fetch_redirect_response=False)

        # User should be deleted
        self.assertFalse(User.objects.filter(email="testuser@example.com").exists())

        # User should be logged out
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_account_delete_logout_after_deletion(self) -> None:
        """Test that user is logged out after account deletion."""
        self.client.force_login(self.user)
        user_id = self.user.pk

        data = {
            "password": "Password123",
            "confirm": True,
        }

        self.client.post(self.account_delete_url, data)

        # Verify user cannot access protected pages
        response = self.client.get(reverse("profile_edit"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore[attr-defined]

        # Verify user is truly deleted from database
        self.assertFalse(User.objects.filter(pk=user_id).exists())


@pytest.mark.django_db
class TestAccountDeleteWithRelatedData:
    """Test account deletion with related data like votes, publications, etc."""

    def test_soft_delete_preserves_user_record(self) -> None:
        """Test that soft delete keeps the user in the database."""
        user = User.objects.create_user(
            email="voter@example.com",
            password="Password123",
            first_name="John",
            last_name="Doe",
            phone_number="0612345678",
        )
        user_id = user.pk
        user_uuid = user.uuid

        user.soft_delete()
        deleted_user = User.objects.with_deleted().get(pk=user_id)

        # Verify user is marked as deleted
        assert deleted_user.is_deleted is True
        assert deleted_user.deleted_at is not None
        assert deleted_user.is_active is False
        assert not deleted_user.has_usable_password()

        # Verify personal data is anonymized
        assert deleted_user.first_name == "Utilisateur"
        assert deleted_user.last_name == "Supprimé"
        assert deleted_user.email == f"deleted.{user_uuid}@deleted.local"
        assert deleted_user.phone_number == ""
        assert deleted_user.newsletter_subscription is False
        assert deleted_user.is_verified is False

        # User should NOT appear in default queryset
        assert not User.objects.filter(pk=user_id).exists()

        # But should appear in deleted_only queryset
        assert User.objects.deleted_only().filter(pk=user_id).exists()

    def test_account_delete_preserves_votes(self) -> None:
        """Test that soft deleting account preserves votes."""

        user = User.objects.create_user(
            email="voter@example.com",
            password="Password123",
            first_name="Voter",
            last_name="Test",
        )
        user_id = user.pk

        # Create a test project page
        home = Page.objects.get(slug="home")
        pub_index = PublicationIndexPage.objects.first()
        if not pub_index:
            pub_index = home.add_child(
                instance=PublicationIndexPage(
                    title="Publications Test",
                    slug="publications-test",
                )
            )

        project = pub_index.add_child(
            instance=ProjectPage(
                title="Test Project",
                slug="test-project",
                description="Test project for anonymization",
            )
        )

        vote = FormResponse.objects.create(
            user=user,
            project=project,
            choice="FAVORABLE",
            comment="Test vote comment",
            anonymize=False,
        )
        vote_id = vote.pk

        # Soft delete the user
        user.soft_delete()

        # Verify vote still exists and points to the soft-deleted user
        vote = FormResponse.objects.get(pk=vote_id)
        assert vote.user.pk == user_id

        # Verify the user is soft-deleted with anonymized data
        deleted_user = User.objects.with_deleted().get(pk=user.pk)
        assert deleted_user.is_deleted is True
        assert deleted_user.first_name == "Utilisateur"
        assert deleted_user.last_name == "Supprimé"

    def test_account_delete_via_view_soft_deletes(self) -> None:
        """Test that deleting account via the view performs soft delete."""

        client = Client()
        user = User.objects.create_user(
            email="voter2@example.com",
            password="Password123",
            first_name="Voter",
            last_name="Test",
            phone_number="0612345678",
        )
        user_id = user.pk
        user_uuid = user.uuid

        # Create a test project page
        home = Page.objects.get(slug="home")
        pub_index = PublicationIndexPage.objects.first()
        if not pub_index:
            pub_index = home.add_child(
                instance=PublicationIndexPage(
                    title="Publications Test 2",
                    slug="publications-test-2",
                )
            )

        project = pub_index.add_child(
            instance=ProjectPage(
                title="Test Project 2",
                slug="test-project-2",
                description="Test project 2 for soft delete",
            )
        )

        vote = FormResponse.objects.create(
            user=user,
            project=project,
            choice="FAVORABLE",
            comment="Test vote comment",
            anonymize=False,
        )
        vote_id = vote.pk

        # Login and delete account via view
        client.force_login(user)
        response = client.post(
            reverse("account_delete"),
            {
                "password": "Password123",
                "confirm": True,
            },
        )

        assert response.status_code == 302  # Redirect after deletion

        # User should not appear in default queryset
        assert not User.objects.filter(pk=user_id).exists()

        # But should exist in with_deleted() queryset
        deleted_user = User.objects.with_deleted().get(pk=user_id)
        assert deleted_user.is_deleted is True

        # Verify anonymization
        assert deleted_user.first_name == "Utilisateur"
        assert deleted_user.last_name == "Supprimé"
        assert deleted_user.email == f"deleted.{user_uuid}@deleted.local"
        assert deleted_user.phone_number == ""

        # Verify vote still exists and points to the soft-deleted user
        vote = FormResponse.objects.get(pk=vote_id)
        assert vote.user.pk == user_id

    def test_multiple_users_soft_deletion(self) -> None:
        """Test that multiple users can be soft deleted without conflicts."""

        # Create a test project page
        home = Page.objects.get(slug="home")
        pub_index = PublicationIndexPage.objects.first()
        if not pub_index:
            pub_index = home.add_child(
                instance=PublicationIndexPage(
                    title="Publications Test 3",
                    slug="publications-test-3",
                )
            )

        project = pub_index.add_child(
            instance=ProjectPage(
                title="Test Project 3",
                slug="test-project-3",
                description="Test project 3 for soft delete",
            )
        )

        # Create two users with votes on the same project
        user1 = User.objects.create_user(
            email="voter1@example.com",
            password="Password123",
            first_name="Voter1",
            last_name="Test",
        )
        vote1 = FormResponse.objects.create(
            user=user1,
            project=project,
            choice="FAVORABLE",
        )

        user2 = User.objects.create_user(
            email="voter3@example.com",
            password="Password123",
            first_name="Voter2",
            last_name="Test",
        )
        vote2 = FormResponse.objects.create(
            user=user2,
            project=project,
            choice="UNFAVORABLE",
        )

        user1_id = user1.pk
        user2_id = user2.pk
        vote1_id = vote1.pk
        vote2_id = vote2.pk

        # Soft delete both users
        user1.soft_delete()
        user2.soft_delete()

        # Verify both users still exist in database (with soft delete)
        deleted_user1 = User.objects.with_deleted().get(pk=user1_id)
        deleted_user2 = User.objects.with_deleted().get(pk=user2_id)

        assert deleted_user1.is_deleted is True
        assert deleted_user2.is_deleted is True

        # Verify both votes still exist
        vote1 = FormResponse.objects.get(pk=vote1_id)
        vote2 = FormResponse.objects.get(pk=vote2_id)

        # Votes point to their respective soft-deleted users (not the same user)
        assert vote1.user.pk == user1_id
        assert vote2.user.pk == user2_id
        assert vote1.user.pk != vote2.user.pk

    def test_soft_deleted_user_cannot_login(self) -> None:
        """Test that a soft-deleted user cannot log in."""

        user = User.objects.create_user(
            email="test@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
        )

        # User can authenticate before deletion
        auth_user = authenticate(email="test@example.com", password="Password123")
        assert auth_user is not None

        # Soft delete the user
        user.soft_delete()

        # User cannot authenticate after soft deletion (unusable password)
        auth_user = authenticate(email=f"deleted.{user.uuid}@deleted.local", password="Password123")
        assert auth_user is None

        # Also check with original email (shouldn't work either)
        auth_user = authenticate(email="test@example.com", password="Password123")
        assert auth_user is None


@pytest.mark.django_db
class TestAccountDeleteForm:
    def test_form_valid_with_correct_password(self) -> None:
        """Test that form is valid with correct password and confirmation."""

        user = User.objects.create_user(
            email="test@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
        )

        form = AccountDeleteForm(
            user=user,
            data={
                "password": "Password123",
                "confirm": True,
            },
        )

        assert form.is_valid()

    def test_form_invalid_with_wrong_password(self) -> None:
        """Test that form is invalid with incorrect password."""

        user = User.objects.create_user(
            email="test@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
        )

        form = AccountDeleteForm(
            user=user,
            data={
                "password": "WrongPassword",
                "confirm": True,
            },
        )

        assert not form.is_valid()
        assert "password" in form.errors

    def test_form_invalid_without_confirmation(self) -> None:
        """Test that form is invalid without confirmation checkbox."""

        user = User.objects.create_user(
            email="test@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
        )

        form = AccountDeleteForm(
            user=user,
            data={
                "password": "Password123",
                "confirm": False,
            },
        )

        assert not form.is_valid()
        assert "confirm" in form.errors
