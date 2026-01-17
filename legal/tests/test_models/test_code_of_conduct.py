from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from legal.models import CodeOfConductPage, LegalIndexPage


class CodeOfConductPageTests(WagtailPageTestCase):
    def setUp(self):
        super().setUp()
        self.home_page = HomePage.objects.first()
        self.legal_index_page = LegalIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()

    def test_can_create_code_of_conduct_page_under_legal_index_page(self):
        self.assertCanCreateAt(LegalIndexPage, CodeOfConductPage)

    def test_cannot_create_code_of_conduct_page_under_other_pages(self):
        self.assertCanNotCreateAt(CodeOfConductPage, CodeOfConductPage)
        self.assertCanNotCreateAt(HomePage, CodeOfConductPage)

    def test_code_of_conduct_page_should_exist(self):
        code_of_conduct_page = CodeOfConductPage.objects.filter(
            path__startswith=self.legal_index_page.path
        ).first()
        self.assertIsNotNone(
            code_of_conduct_page,
            "CodeOfConductPage does not exist under LegalIndexPage.",
        )
