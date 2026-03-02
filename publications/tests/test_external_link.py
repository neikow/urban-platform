from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page

from publications.factories.project_factory import ProjectPageFactory
from publications.models import ProjectExternalLink


class ProjectExternalLinkTest(TestCase):
    """Test cases for ProjectExternalLink model."""

    @classmethod
    def setUpTestData(cls) -> None:
        root = Page.get_first_root_node()
        cls.project = ProjectPageFactory.create(parent=root)

    def test_create_external_link(self) -> None:
        """Test creating an external link for a project."""
        link = ProjectExternalLink(
            page=self.project,
            title="Voir le site officiel",
            url="https://example.com/docs",
            tooltip="Accéder à la documentation officielle",
        )
        link.clean()
        link.save()

        self.assertEqual(link.title, "Voir le site officiel")
        self.assertEqual(link.url, "https://example.com/docs")
        self.assertEqual(link.tooltip, "Accéder à la documentation officielle")
        self.assertEqual(str(link), "Voir le site officiel")

    def test_create_external_link_without_tooltip(self) -> None:
        """Test creating an external link without a tooltip."""
        link = ProjectExternalLink(
            page=self.project,
            title="Lien simple",
            url="https://example.com",
        )
        link.clean()
        link.save()

        self.assertEqual(link.tooltip, "")

    def test_external_link_url_required(self) -> None:
        """Test that URL is required for external links."""
        link = ProjectExternalLink(
            page=self.project,
            title="No URL",
            url="",
        )
        with self.assertRaises(ValidationError) as cm:
            link.clean()

        self.assertIn(
            str(_("URL is required for external links.")),
            str(cm.exception),
        )

    def test_project_has_external_links_property(self) -> None:
        """Test the has_external_links property on ProjectPage."""
        # Initially, no links
        self.assertFalse(self.project.has_external_links)

        # Add a link
        ProjectExternalLink.objects.create(
            page=self.project,
            title="Test Link",
            url="https://example.com",
        )

        self.assertTrue(self.project.has_external_links)

    def test_project_external_links_relation(self) -> None:
        """Test the external_links relation on ProjectPage."""
        link1 = ProjectExternalLink.objects.create(
            page=self.project,
            title="Link 1",
            url="https://example1.com",
            sort_order=1,
        )
        link2 = ProjectExternalLink.objects.create(
            page=self.project,
            title="Link 2",
            url="https://example2.com",
            sort_order=0,
        )

        links = [link1, link2]
        # Should be ordered by sort_order
        self.assertEqual(links[0].title, "Link 2")
        self.assertEqual(links[1].title, "Link 1")

    def test_multiple_external_links(self) -> None:
        """Test creating multiple external links for a project."""
        ProjectExternalLink.objects.create(
            page=self.project,
            title="Signer la pétition",
            url="https://petition.example.com",
            tooltip="Ajoutez votre signature",
        )
        ProjectExternalLink.objects.create(
            page=self.project,
            title="Document officiel",
            url="https://docs.example.com/report.pdf",
            tooltip="Télécharger le rapport",
        )

        links = self.project.external_links.all()
        self.assertEqual(links.count(), 2)
