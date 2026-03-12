from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from about.models import AboutIndexPage, AboutCommissionPage


class AboutCommissionPageTests(WagtailPageTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.home_page = HomePage.objects.first()
        self.about_index = AboutIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()

    def test_can_create_about_commission_page_under_about_index(self) -> None:
        self.assertCanCreateAt(AboutIndexPage, AboutCommissionPage)

    def test_cannot_create_about_commission_page_under_other_pages(self) -> None:
        self.assertCanNotCreateAt(AboutCommissionPage, AboutCommissionPage)
        self.assertCanNotCreateAt(HomePage, AboutCommissionPage)

    def test_about_commission_page_should_exist(self) -> None:
        page = AboutCommissionPage.objects.filter(path__startswith=self.about_index.path).first()
        self.assertIsNotNone(page, "AboutCommissionPage does not exist under AboutIndexPage.")
