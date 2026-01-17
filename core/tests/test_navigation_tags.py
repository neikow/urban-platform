from django.test import TestCase, RequestFactory
from django.template import Context, Template
from wagtail.models import Site, Page
from core.templatetags.navigation_tags import get_site_root


class NavigationTagsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_site_root_returns_root_page(self):
        site = Site.objects.get(is_default_site=True)
        request = self.factory.get("/")
        context = {"request": request}

        root_page = get_site_root(context)

        self.assertIsInstance(root_page, Page)
        self.assertEqual(root_page, site.root_page)

    def test_get_site_root_in_template(self):
        site = Site.objects.get(is_default_site=True)
        request = self.factory.get("/")

        template = Template(
            "{% load navigation_tags %}"
            "{% get_site_root as site_root %}"
            "{{ site_root.id }}"
        )

        context = Context({"request": request})
        rendered = template.render(context)

        self.assertEqual(rendered.strip(), str(site.root_page.id))

    def test_get_site_root_with_custom_site(self):
        default_site = Site.objects.get(is_default_site=True)
        root_page = default_site.root_page

        new_root = Page(title="Custom Root", slug="custom-root")
        root_page.add_child(instance=new_root)

        custom_site = Site.objects.create(
            hostname="custom.example.com",
            port=80,
            root_page=new_root,
            is_default_site=False,
            site_name="Custom Site",
        )

        request = self.factory.get("/", HTTP_HOST="custom.example.com")
        context = {"request": request}

        root_page_result = get_site_root(context)

        self.assertIsInstance(root_page_result, Page)
        self.assertEqual(root_page_result, custom_site.root_page)
        self.assertEqual(root_page_result.title, "Custom Root")

    def test_get_site_root_no_request_in_context(self):
        site = Site.objects.get(is_default_site=True)
        context = {}

        root_page = get_site_root(context)

        self.assertEqual(root_page, site.root_page)

    def test_get_site_root_unknown_host_fallback(self):
        request = self.factory.get("/", HTTP_HOST="unknown.server.com")
        context = {"request": request}
        site = Site.objects.get(is_default_site=True)

        root_page = get_site_root(context)

        self.assertEqual(root_page, site.root_page)

    def test_get_site_root_no_sites_exist(self):
        Site.objects.all().delete()
        context = {}

        root_page = get_site_root(context)

        self.assertIsNone(root_page)
