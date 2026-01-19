from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from legal.models import TermsOfServicePage, LegalIndexPage


class TermsOfServicePageTests(WagtailPageTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.home_page = HomePage.objects.first()
        self.legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()

    def test_can_create_terms_of_service_page_under_legal_index_page(self) -> None:
        self.assertCanCreateAt(LegalIndexPage, TermsOfServicePage)

    def test_cannot_create_terms_of_service_page_under_other_pages(self) -> None:
        self.assertCanNotCreateAt(TermsOfServicePage, TermsOfServicePage)
        self.assertCanNotCreateAt(HomePage, TermsOfServicePage)

    def test_terms_of_service_page_should_exist(self) -> None:
        page = TermsOfServicePage.objects.filter(
            path__startswith=self.legal_index_page.path
        ).first()
        self.assertIsNotNone(page, "TermsOfServicePage does not exist under LegalIndexPage.")
