from django.test import TestCase, RequestFactory, override_settings
from django.template.loader import render_to_string
from wagtail.models import Site, Page
from home.models import HomePage
from pedagogy.models import PedagogyIndexPage


class HeaderComponentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        root = Page.get_first_root_node()

        cls.home = HomePage.objects.child_of(root).first()
        if not cls.home:
            cls.home = HomePage(title="Home", slug="home")
            root.add_child(instance=cls.home)

        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            site = Site.objects.create(
                hostname="localhost",
                root_page=cls.home,
                is_default_site=True,
                site_name="Test Site",
            )
        else:
            site.root_page = cls.home
            site.save()

        cls.page1 = Page(title="Page 1", slug="page-1", show_in_menus=True)
        cls.home.add_child(instance=cls.page1)

        cls.page2 = Page(title="Page 2", slug="page-2", show_in_menus=True)
        cls.home.add_child(instance=cls.page2)

    def test_header_render(self):
        factory = RequestFactory()
        request = factory.get("/")

        context = {"request": request}

        rendered = render_to_string("core/components/website_header.html", context)

        self.assertIn("Page 1", rendered)
        self.assertIn("Page 2", rendered)
        self.assertIn("navbar-start", rendered)
        self.assertIn("navbar-center", rendered)
        self.assertIn("dropdown", rendered)
