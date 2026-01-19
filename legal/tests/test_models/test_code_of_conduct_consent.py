from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from wagtail.models import Page

from home.models import HomePage
from legal.models import CodeOfConductPage, CodeOfConductConsent, LegalIndexPage


class CodeOfConductConsentTests(TestCase):
    def setUp(self) -> None:
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            password="testpassword", email="testuser@example.com"
        )
        self.superuser = self.User.objects.create_superuser(
            password="adminpassword", email="admin@example.com"
        )

        root = Page.get_first_root_node()
        self.home_page = HomePage.objects.child_of(root).first()
        if not self.home_page:
            self.home_page = HomePage(title="Home", slug="home")
            root.add_child(instance=self.home_page)

        self.legal_index = (
            LegalIndexPage.objects.child_of(self.home_page).filter(slug="legal").first()
        )
        if not self.legal_index:
            self.legal_index = LegalIndexPage(title="Legal", slug="legal")
            self.home_page.add_child(instance=self.legal_index)

        self.code_of_conduct_page = (
            CodeOfConductPage.objects.child_of(self.legal_index)
            .filter(slug="code-of-conduct")
            .first()
        )
        if not self.code_of_conduct_page:
            self.code_of_conduct_page = CodeOfConductPage(
                title="Code of Conduct",
                slug="code-of-conduct",
                content="Initial content",
            )
            self.legal_index.add_child(instance=self.code_of_conduct_page)

        self.initial_revision = self.code_of_conduct_page.save_revision()
        self.initial_revision.publish()

    def test_create_consent(self) -> None:
        consent = CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=self.initial_revision,
            consent_ip="127.0.0.1",
        )
        self.assertEqual(CodeOfConductConsent.objects.count(), 1)
        self.assertEqual(consent.user, self.user)
        self.assertEqual(consent.policy_revision, self.initial_revision)
        self.assertEqual(consent.consent_ip, "127.0.0.1")
        self.assertIsNotNone(consent.consented_at)

    def test_unique_consent_per_version(self) -> None:
        CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=self.initial_revision,
        )

        with self.assertRaises(IntegrityError):
            CodeOfConductConsent.objects.create(
                user=self.user,
                policy_revision=self.initial_revision,
            )

    def test_is_up_to_date_with_latest_revision(self) -> None:
        consent = CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=self.initial_revision,
        )
        self.assertTrue(consent.is_up_to_date())

    def test_is_up_to_date_with_outdated_revision(self) -> None:
        consent = CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=self.initial_revision,
        )

        self.code_of_conduct_page.content = "Updated content"
        self.code_of_conduct_page.save_revision().publish()

        self.assertFalse(consent.is_up_to_date())

    def test_str_representation(self) -> None:
        consent = CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=self.initial_revision,
        )
        expected_str = (
            f"{self.user} consent to Code Of Conduct ({self.initial_revision.created_at})"
        )
        self.assertEqual(str(consent), expected_str)

    def test_user_can_consent_to_multiple_revisions(self) -> None:
        CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=self.initial_revision,
        )

        self.code_of_conduct_page.content = "V2 Content"
        new_revision = self.code_of_conduct_page.save_revision()
        new_revision.publish()

        consent_v2 = CodeOfConductConsent.objects.create(
            user=self.user,
            policy_revision=new_revision,
        )

        self.assertEqual(CodeOfConductConsent.objects.filter(user=self.user).count(), 2)
        self.assertTrue(consent_v2.is_up_to_date())
