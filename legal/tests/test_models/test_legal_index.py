from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from legal.models import LegalIndexPage


class LegalIndexPageTests(WagtailPageTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.home_page = HomePage.objects.first()

    def test_can_create_legal_index_page_under_home_page(self) -> None:
        self.assertCanCreateAt(HomePage, LegalIndexPage)

    def test_cannot_create_legal_index_page_under_other_pages(self) -> None:
        self.assertCanNotCreateAt(LegalIndexPage, LegalIndexPage)

    def test_legal_index_page_should_exist(self) -> None:
        legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()
        self.assertIsNotNone(
            legal_index_page, "LegalIndexPage does not exist under HomePage."
        )

    def test_legal_index_page_is_subpage_of_home_page(self) -> None:
        legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()
        self.assertIsNotNone(
            legal_index_page, "LegalIndexPage does not exist under HomePage."
        )
        self.assertEqual(
            legal_index_page.get_parent().id,
            self.home_page.id,
            "LegalIndexPage is not a child of HomePage.",
        )

    def test_legal_index_page_slug(self) -> None:
        legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()
        self.assertIsNotNone(
            legal_index_page, "LegalIndexPage does not exist under HomePage."
        )
        self.assertEqual(
            legal_index_page.slug, "legal", "LegalIndexPage slug is not 'legal'."
        )
