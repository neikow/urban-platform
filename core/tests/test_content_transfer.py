import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from wagtail.documents.models import Document
from wagtail.images.models import Image

from core.management.commands._content_transfer import collect_media_ids
from core.tests.utils.factories import DocumentFactory
from pedagogy.models.pedagogy_card import PedagogyCardPage
from pedagogy.models.pedagogy_index import PedagogyIndexPage
from pedagogy.models.pedagogy_resource import PedagogyResource
from publications.factories import ProjectPageFactory
from publications.models.external_link import ProjectExternalLink
from publications.models.project import ProjectPage
from publications.models.publication_index import PublicationIndexPage


class ContentTransferTestCase(TestCase):
    def setUp(self) -> None:
        # Home + index pages are seeded by data migrations (one of each,
        # max_count=1), matching what the command resolves on import.
        self.publication_index = PublicationIndexPage.objects.get()
        self.pedagogy_index = PedagogyIndexPage.objects.get()

        self.project: ProjectPage = ProjectPageFactory.create(
            parent=self.publication_index,
            title="Mobilité douce",
            slug="mobilite-douce",
        )
        ProjectExternalLink.objects.create(
            page=self.project, title="En savoir plus", url="https://example.com", tooltip="Info"
        )

        self.card: PedagogyCardPage = PedagogyCardPage(
            title="Comprendre le PLU", slug="comprendre-le-plu", description="Une fiche"
        )
        self.pedagogy_index.add_child(instance=self.card)
        self.doc = DocumentFactory.create()
        PedagogyResource.objects.create(page=self.card, document=self.doc)

    def _export(self) -> Path:
        archive = Path(tempfile.mkdtemp()) / "content.zip"
        call_command("export_content", "--output", str(archive))
        return archive

    def test_round_trip_reconstructs_content_after_wipe(self) -> None:
        hero_pk = self.project.hero_image_id
        content_image_ids, _ = collect_media_ids(self.project.content.get_prep_value())
        self.assertTrue(content_image_ids, "fixture should embed at least one image")

        archive = self._export()

        # Simulate a fresh destination environment.
        ProjectPage.objects.all().delete()
        PedagogyCardPage.objects.all().delete()
        Image.objects.all().delete()
        Document.objects.all().delete()
        self.assertEqual(ProjectPage.objects.count(), 0)

        call_command("import_content", str(archive))

        project = ProjectPage.objects.get(slug="mobilite-douce")
        self.assertEqual(project.title, "Mobilité douce")
        self.assertEqual(project.get_parent().id, self.publication_index.id)

        # Hero image restored under its original pk; references stay valid.
        self.assertEqual(project.hero_image_id, hero_pk)
        self.assertTrue(Image.objects.filter(pk=hero_pk).exists())

        # Embedded content images restored.
        restored_ids, _ = collect_media_ids(project.content.get_prep_value())
        self.assertEqual(restored_ids, content_image_ids)
        for image_id in restored_ids:
            self.assertTrue(Image.objects.filter(pk=image_id).exists())

        # Orderable external links restored.
        links = list(project.external_links.all())
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].title, "En savoir plus")

        # Pedagogy card + its document resource restored.
        card = PedagogyCardPage.objects.get(slug="comprendre-le-plu")
        resources = list(card.resources.all())
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].document_id, self.doc.pk)
        self.assertTrue(Document.objects.filter(pk=self.doc.pk).exists())

    def test_import_is_idempotent(self) -> None:
        archive = self._export()

        call_command("import_content", str(archive))
        call_command("import_content", str(archive))

        # Upsert by slug: no duplicates created on repeat import.
        self.assertEqual(ProjectPage.objects.filter(slug="mobilite-douce").count(), 1)
        self.assertEqual(PedagogyCardPage.objects.filter(slug="comprendre-le-plu").count(), 1)
        self.assertEqual(self.project.external_links.count(), 1)

    def test_import_updates_existing_page_fields(self) -> None:
        archive = self._export()

        # Mutate the live page, then re-importing the archive should restore it.
        self.project.title = "Titre modifié"
        self.project.save_revision().publish()

        call_command("import_content", str(archive))

        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Mobilité douce")
