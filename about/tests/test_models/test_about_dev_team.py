from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage
from about.models import AboutIndexPage, AboutDevTeamPage


class AboutDevTeamPageTests(WagtailPageTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.home_page = HomePage.objects.first()
        self.about_index = AboutIndexPage.objects.filter(
            path__startswith=self.home_page.path
        ).first()

    def test_can_create_about_dev_team_page_under_about_index(self) -> None:
        self.assertCanCreateAt(AboutIndexPage, AboutDevTeamPage)

    def test_cannot_create_about_dev_team_page_under_other_pages(self) -> None:
        self.assertCanNotCreateAt(AboutDevTeamPage, AboutDevTeamPage)
        self.assertCanNotCreateAt(HomePage, AboutDevTeamPage)

    def test_about_dev_team_page_should_exist(self) -> None:
        page = AboutDevTeamPage.objects.filter(path__startswith=self.about_index.path).first()
        self.assertIsNotNone(page, "AboutDevTeamPage does not exist under AboutIndexPage.")
