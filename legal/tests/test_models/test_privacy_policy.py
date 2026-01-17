from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from legal.models import PrivacyPolicyPage, LegalIndexPage


class PrivacyPolicyPageTests(WagtailPageTestCase):
    def setUp(self):
        super().setUp()
        self.home_page = HomePage.objects.first()
        self.legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()

    def test_can_create_privacy_policy_page_under_legal_index_page(self):
        self.assertCanCreateAt(LegalIndexPage, PrivacyPolicyPage)

    def test_cannot_create_privacy_policy_page_under_other_pages(self):
        self.assertCanNotCreateAt(PrivacyPolicyPage, PrivacyPolicyPage)
        self.assertCanNotCreateAt(HomePage, PrivacyPolicyPage)

    def test_privacy_policy_page_should_exist(self):
        page = PrivacyPolicyPage.objects.filter(
            path__startswith=self.legal_index_page.path
        ).first()
        self.assertIsNotNone(
            page, "PrivacyPolicyPage does not exist under LegalIndexPage."
        )
