from datetime import timedelta

from django.test import TestCase, RequestFactory
from django.utils import timezone
from wagtail.rich_text import RichText

from home.models import HomePage
from publications.models import ProjectPage, PublicationIndexPage, ProjectCategory, EventPage


class ProjectPageModelTest(TestCase):
    project_index: PublicationIndexPage

    @classmethod
    def setUpTestData(cls) -> None:
        home_page = HomePage.objects.get(slug="home")
        cls.project_index = PublicationIndexPage(title="Projects", slug="projects")
        home_page.add_child(instance=cls.project_index)

    def test_project_creation_with_default_category(self) -> None:
        project = ProjectPage(title="Test Project", description="Test description")
        self.project_index.add_child(instance=project)

        self.assertEqual(project.title, "Test Project")
        self.assertEqual(project.description, "Test description")
        self.assertEqual(project.category, ProjectCategory.OTHER)

    def test_project_all_categories_valid(self) -> None:
        for category_value, _ in ProjectCategory.choices:
            project = ProjectPage(title=f"Project {category_value}", category=category_value)
            self.project_index.add_child(instance=project)
            self.assertEqual(project.category, category_value)

    def test_table_of_contents_empty_when_no_content(self) -> None:
        project = ProjectPage(title="Empty Project")
        self.project_index.add_child(instance=project)
        self.assertEqual(project.table_of_contents, [])

    def test_table_of_contents_extracts_headers(self) -> None:
        project = ProjectPage(
            title="Project with TOC",
            category=ProjectCategory.URBAN_PLANNING,
            content=[
                (
                    "text",
                    RichText(
                        "<h2 id='intro'>Introduction</h2><p>Text</p>"
                        "<h3 id='context'>Context</h3><p>More</p>"
                        "<h2 id='conclusion'>Conclusion</h2>"
                    ),
                )
            ],
        )

        toc = project.table_of_contents
        self.assertEqual(len(toc), 3)
        self.assertEqual(toc[0].title, "Introduction")
        self.assertEqual(toc[0].level, 2)
        self.assertEqual(toc[1].title, "Context")
        self.assertEqual(toc[1].level, 3)


class EventPageModelTest(TestCase):
    publication_index: PublicationIndexPage

    @classmethod
    def setUpTestData(cls) -> None:
        home_page = HomePage.objects.get(slug="home")
        cls.publication_index = PublicationIndexPage(title="Publications", slug="publications")
        home_page.add_child(instance=cls.publication_index)

    def test_event_creation_with_all_fields(self) -> None:
        event = EventPage(
            title="Test Event",
            description="Event description",
            event_date=timezone.now() + timedelta(days=7),
            end_date=timezone.now() + timedelta(days=7, hours=3),
            location="Test Location",
            address="123 Test Street",
            is_online=True,
            online_link="https://example.com/meeting",
            max_participants=50,
        )
        self.publication_index.add_child(instance=event)

        self.assertEqual(event.title, "Test Event")
        self.assertEqual(event.location, "Test Location")
        self.assertTrue(event.is_online)
        self.assertEqual(event.max_participants, 50)

    def test_is_past_and_is_upcoming_properties(self) -> None:
        future_event = EventPage(
            title="Future Event",
            event_date=timezone.now() + timedelta(days=7),
        )
        self.publication_index.add_child(instance=future_event)

        past_event = EventPage(
            title="Past Event",
            event_date=timezone.now() - timedelta(days=7),
        )
        self.publication_index.add_child(instance=past_event)

        self.assertFalse(future_event.is_past)
        self.assertTrue(future_event.is_upcoming)
        self.assertTrue(past_event.is_past)
        self.assertFalse(past_event.is_upcoming)

    def test_is_past_uses_end_date_when_available(self) -> None:
        ongoing_event = EventPage(
            title="Ongoing Seminar",
            event_date=timezone.now() - timedelta(days=1),  # commencé hier
            end_date=timezone.now() + timedelta(days=2),  # finit dans 2 jours
        )
        self.publication_index.add_child(instance=ongoing_event)

        self.assertFalse(ongoing_event.is_past)
        self.assertTrue(ongoing_event.is_upcoming)

    def test_is_past_with_end_date_in_past(self) -> None:
        finished_event = EventPage(
            title="Finished Seminar",
            event_date=timezone.now() - timedelta(days=5),
            end_date=timezone.now() - timedelta(days=2),
        )
        self.publication_index.add_child(instance=finished_event)

        self.assertTrue(finished_event.is_past)
        self.assertFalse(finished_event.is_upcoming)


class PublicationIndexPageModelTest(TestCase):
    publication_index: PublicationIndexPage
    factory: RequestFactory

    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()
        home_page = HomePage.objects.get(slug="home")

        cls.publication_index = PublicationIndexPage(
            title="Publications",
            slug="publications",
            page_introduction="Test introduction",
        )
        home_page.add_child(instance=cls.publication_index)

        project1 = ProjectPage(title="Urban Project", category=ProjectCategory.URBAN_PLANNING)
        cls.publication_index.add_child(instance=project1)
        project1.save_revision().publish()

        project2 = ProjectPage(title="Environment Project", category=ProjectCategory.ENVIRONMENT)
        cls.publication_index.add_child(instance=project2)
        project2.save_revision().publish()

        event = EventPage(title="Future Event", event_date=timezone.now() + timedelta(days=7))
        cls.publication_index.add_child(instance=event)
        event.save_revision().publish()

    def test_get_publications_filters_by_type(self) -> None:
        request = self.factory.get("/publications/")
        self.assertEqual(len(self.publication_index.get_publications(request)), 3)

        request = self.factory.get("/publications/?type=projects")
        self.assertEqual(len(self.publication_index.get_publications(request)), 2)

        request = self.factory.get("/publications/?type=events")
        self.assertEqual(len(self.publication_index.get_publications(request)), 1)

    def test_get_publications_filters_by_category(self) -> None:
        request = self.factory.get("/publications/?type=projects&category=URBAN_PLANNING")
        publications = self.publication_index.get_publications(request)

        self.assertEqual(len(publications), 1)
        self.assertEqual(publications[0].title, "Urban Project")

    def test_get_publications_ignores_invalid_category(self) -> None:
        request = self.factory.get("/publications/?type=projects&category=INVALID")
        publications = self.publication_index.get_publications(request)
        self.assertEqual(len(publications), 2)

    def test_get_publications_search(self) -> None:
        project = ProjectPage(title="Searchable", description="Contains keyword findme")
        self.publication_index.add_child(instance=project)
        project.save_revision().publish()

        request = self.factory.get("/publications/?type=projects&search=findme")
        publications = self.publication_index.get_publications(request)

        self.assertEqual(len(publications), 1)
        self.assertEqual(publications[0].title, "Searchable")

    def test_get_publications_pagination(self) -> None:
        for i in range(15):
            project = ProjectPage(title=f"Project {i}", category=ProjectCategory.OTHER)
            self.publication_index.add_child(instance=project)
            project.save_revision().publish()

        request = self.factory.get("/publications/?type=projects&page=1")
        self.assertEqual(len(self.publication_index.get_publications(request)), 12)

        request = self.factory.get("/publications/?type=projects&page=2")
        self.assertEqual(len(self.publication_index.get_publications(request)), 5)

    def test_get_context_returns_expected_keys(self) -> None:
        request = self.factory.get("/publications/?type=events&category=URBAN_PLANNING")
        context = self.publication_index.get_context(request)

        self.assertIn("publications", context)
        self.assertIn("categories", context)
        self.assertEqual(context["selected_type"], "events")
        self.assertEqual(context["selected_category"], "URBAN_PLANNING")
