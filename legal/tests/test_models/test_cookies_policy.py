from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from legal.models import CookiesPolicyPage, LegalIndexPage


class CookiesPolicyPageTests(WagtailPageTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.home_page = HomePage.objects.first()
        self.legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()

    def test_can_create_cookies_policy_page_under_legal_index_page(self) -> None:
        self.assertCanCreateAt(LegalIndexPage, CookiesPolicyPage)

    def test_cannot_create_cookies_policy_page_under_other_pages(self) -> None:
        self.assertCanNotCreateAt(CookiesPolicyPage, CookiesPolicyPage)
        self.assertCanNotCreateAt(HomePage, CookiesPolicyPage)

    def test_cookies_policy_page_should_exist(self) -> None:
        page = CookiesPolicyPage.objects.filter(
            path__startswith=self.legal_index_page.path
        ).first()
        self.assertIsNotNone(
            page, "CookiesPolicyPage does not exist under LegalIndexPage."
        )
