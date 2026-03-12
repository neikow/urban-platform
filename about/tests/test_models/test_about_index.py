from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from about.models import AboutIndexPage


class AboutIndexPageTests(WagtailPageTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.home_page = HomePage.objects.first()

    def test_can_create_about_index_page_under_home_page(self) -> None:
        self.assertCanCreateAt(HomePage, AboutIndexPage)

    def test_cannot_create_about_index_page_under_other_pages(self) -> None:
        self.assertCanNotCreateAt(AboutIndexPage, AboutIndexPage)

    def test_about_index_page_should_exist(self) -> None:
        about_index = AboutIndexPage.objects.filter(path__startswith=self.home_page.path).first()
        self.assertIsNotNone(about_index, "AboutIndexPage does not exist under HomePage.")

    def test_about_index_page_is_subpage_of_home_page(self) -> None:
        about_index = AboutIndexPage.objects.filter(path__startswith=self.home_page.path).first()
        self.assertIsNotNone(about_index, "AboutIndexPage does not exist under HomePage.")
        self.assertEqual(
            about_index.get_parent().id,
            self.home_page.id,
            "AboutIndexPage is not a child of HomePage.",
        )

    def test_about_index_page_slug(self) -> None:
        about_index = AboutIndexPage.objects.filter(path__startswith=self.home_page.path).first()
        self.assertIsNotNone(about_index, "AboutIndexPage does not exist under HomePage.")
        self.assertEqual(about_index.slug, "about", "AboutIndexPage slug is not 'about'.")
