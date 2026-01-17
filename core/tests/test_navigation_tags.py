from django.template.context import BaseContext
from django.test import TestCase, RequestFactory
from django.template import Context, Template
from wagtail.models import Site, Page
from core.templatetags.navigation_tags import get_site_root, get_legal_pages


class SiteRootTagTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_get_site_root_returns_root_page(self) -> None:
        site = Site.objects.get(is_default_site=True)
        request = self.factory.get("/")
        context = BaseContext({"request": request})

        root_page = get_site_root(context)

        self.assertIsInstance(root_page, Page)
        self.assertEqual(root_page, site.root_page)

    def test_get_site_root_in_template(self) -> None:
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

    def test_get_site_root_with_custom_site(self) -> None:
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
        context = BaseContext({"request": request})

        root_page_result = get_site_root(context)

        self.assertIsInstance(root_page_result, Page)
        self.assertEqual(root_page_result, custom_site.root_page)
        self.assertEqual(
            root_page_result.title,  # type: ignore[union-attr]
            "Custom Root",
        )

    def test_get_site_root_no_request_in_context(self) -> None:
        site = Site.objects.get(is_default_site=True)
        context = BaseContext()

        root_page = get_site_root(context)

        self.assertEqual(root_page, site.root_page)

    def test_get_site_root_unknown_host_fallback(self) -> None:
        request = self.factory.get("/", HTTP_HOST="unknown.server.com")
        context = BaseContext({"request": request})
        site = Site.objects.get(is_default_site=True)

        root_page = get_site_root(context)

        self.assertEqual(root_page, site.root_page)

    def test_get_site_root_no_sites_exist(self) -> None:
        Site.objects.all().delete()
        context = BaseContext()

        root_page = get_site_root(context)

        self.assertIsNone(root_page)


class LegalPagesTagTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_get_legal_pages(self) -> None:
        from legal.models import LegalIndexPage, TermsOfServicePage

        LegalIndexPage.objects.all().delete()

        site = Site.objects.get(is_default_site=True)
        root = site.root_page

        legal_index = LegalIndexPage(title="Legal", slug="legal_index")
        root.add_child(instance=legal_index)

        page1 = TermsOfServicePage(title="Terms", slug="terms", show_in_menus=True)
        legal_index.add_child(instance=page1)

        page2 = TermsOfServicePage(title="Privacy", slug="privacy", show_in_menus=False)
        legal_index.add_child(instance=page2)

        request = self.factory.get("/")
        context = BaseContext({"request": request})

        pages = get_legal_pages(context)

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].title, "Terms")

    def test_get_legal_pages_no_index(self) -> None:
        from legal.models import LegalIndexPage

        LegalIndexPage.objects.all().delete()

        request = self.factory.get("/")
        context = BaseContext({"request": request})

        pages = get_legal_pages(context)

        self.assertEqual(len(pages), 0)
