from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.documents.models import Document
from wagtail.models import Page
from django.utils.translation import gettext_lazy as _

from pedagogy.models import PedagogyCardPage
from pedagogy.models.pedagogy_resource import PedagogyResource
from pedagogy.factories.pedagogy_card_factory import PedagogyCardPageFactory


class PedagogyResourceTest(TestCase):
    page: PedagogyCardPage
    doc: Document

    @classmethod
    def setUpTestData(cls) -> None:
        root = Page.get_first_root_node()
        cls.page = PedagogyCardPageFactory.create(parent=root)
        cls.doc = Document.objects.create(title="Test Doc", file="test.pdf")

    def test_resource_with_url_valid(self) -> None:
        resource = PedagogyResource(page=self.page, url="https://example.com")
        # Should not raise
        resource.clean()
        resource.save()

    def test_resource_with_document_valid(self) -> None:
        resource = PedagogyResource(page=self.page, document=self.doc)
        # Should not raise
        resource.clean()
        resource.save()

    def test_resource_mutual_exclusivity(self) -> None:
        resource = PedagogyResource(
            page=self.page,
            url="https://example.com",
            document=self.doc,
        )
        with self.assertRaises(ValidationError) as cm:
            resource.clean()

        self.assertIn(
            str(_("Please provide either a URL or a Document, but not both.")),
            str(cm.exception),
        )

    def test_resource_required_fields(self) -> None:
        resource = PedagogyResource(page=self.page)
        with self.assertRaises(ValidationError) as cm:
            resource.clean()

        self.assertIn(
            str(_("Please provide either a URL or a Document.")),
            str(cm.exception),
        )
