from django.test import TestCase, RequestFactory
from django.template import Context, Template
from wagtail.models import Site, Page
from core.templatetags.navigation_tags import get_site_root


class NavigationTagsTest(TestCase):
    def setUp(self):
        """Set up test data for navigation tags tests."""
        self.factory = RequestFactory()
        
    def test_get_site_root_returns_root_page(self):
        """Test that get_site_root returns the root page for the default site."""
        # Get the default site
        site = Site.objects.get(is_default_site=True)
        
        # Create a mock request
        request = self.factory.get('/')
        
        # Create a context with the request
        context = {'request': request}
        
        # Call the template tag
        root_page = get_site_root(context)
        
        # Assert that we got the root page
        self.assertIsInstance(root_page, Page)
        self.assertEqual(root_page, site.root_page)
        
    def test_get_site_root_in_template(self):
        """Test that get_site_root works correctly when used in a template."""
        # Get the default site
        site = Site.objects.get(is_default_site=True)
        
        # Create a mock request
        request = self.factory.get('/')
        
        # Create a template using the tag
        template = Template(
            "{% load navigation_tags %}"
            "{% get_site_root as site_root %}"
            "{{ site_root.id }}"
        )
        
        # Render the template with context
        context = Context({'request': request})
        rendered = template.render(context)
        
        # Assert that the rendered output contains the root page ID
        self.assertEqual(rendered.strip(), str(site.root_page.id))
        
    def test_get_site_root_with_custom_site(self):
        """Test that get_site_root returns the correct root page for a custom site."""
        # Get the default site
        default_site = Site.objects.get(is_default_site=True)
        root_page = default_site.root_page
        
        # Create a new page under the root
        new_root = Page(title="Custom Root", slug="custom-root")
        root_page.add_child(instance=new_root)
        
        # Create a custom site with a different hostname
        custom_site = Site.objects.create(
            hostname='custom.example.com',
            port=80,
            root_page=new_root,
            is_default_site=False,
            site_name='Custom Site'
        )
        
        # Create a mock request for the custom site
        request = self.factory.get('/', HTTP_HOST='custom.example.com')
        
        # Create a context with the request
        context = {'request': request}
        
        # Call the template tag
        root_page_result = get_site_root(context)
        
        # Assert that we got the custom site's root page
        self.assertIsInstance(root_page_result, Page)
        self.assertEqual(root_page_result, custom_site.root_page)
        self.assertEqual(root_page_result.title, "Custom Root")
