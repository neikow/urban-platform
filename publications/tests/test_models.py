from datetime import timedelta

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.utils.translation import gettext as _
from wagtail.rich_text import RichText

from core.blocks import BLOCK_TYPE_RICH_TEXT, TextJustification
from home.models import HomePage
from publications.models import ProjectPage, PublicationIndexPage, EventPage, Rubric, RubricCode


def rubrics(*codes: str) -> list[Rubric]:
    return list(Rubric.objects.filter(code__in=codes))


class ProjectPageModelTest(TestCase):
    project_index: PublicationIndexPage

    @classmethod
    def setUpTestData(cls) -> None:
        home_page = HomePage.objects.get(slug="home")
        cls.project_index = PublicationIndexPage(title="Projects", slug="projects")
        home_page.add_child(instance=cls.project_index)

    def test_project_creation(self) -> None:
        project = ProjectPage(title="Test Project", description="Test description")
        self.project_index.add_child(instance=project)

        self.assertEqual(project.title, "Test Project")
        self.assertEqual(project.description, "Test description")
        self.assertEqual(project.rubric_labels, [])

    def test_project_belongs_to_several_rubrics_in_display_order(self) -> None:
        project = ProjectPage(
            title="Several rubrics", rubrics=rubrics(RubricCode.HERITAGE, RubricCode.HOUSING)
        )
        self.project_index.add_child(instance=project)
        project.save_revision().publish()

        project = ProjectPage.objects.get(pk=project.pk)
        self.assertEqual(
            [r.code for r in project.rubrics.all()], [RubricCode.HOUSING, RubricCode.HERITAGE]
        )
        self.assertEqual(len(project.rubric_labels), 2)

    def test_rubrics_are_required_in_the_editor(self) -> None:
        form_class = ProjectPage.get_edit_handler().get_form_class()
        self.assertTrue(form_class.base_fields["rubrics"].required)

    def test_table_of_contents_empty_when_no_content(self) -> None:
        project = ProjectPage(title="Empty Project")
        self.project_index.add_child(instance=project)
        self.assertEqual(project.table_of_contents, [])

    def test_table_of_contents_extracts_headers(self) -> None:
        project = ProjectPage(
            title="Project with TOC",
            content=[
                (
                    BLOCK_TYPE_RICH_TEXT,
                    {
                        "text": RichText(
                            "<h2 id='intro'>Introduction</h2><p>Text</p>"
                            "<h3 id='context'>Context</h3><p>More</p>"
                            "<h2 id='conclusion'>Conclusion</h2>"
                        ),
                        "justification": TextJustification.LEFT,
                    },
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
        cls.publication_index = PublicationIndexPage.objects.first()

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
        self.assertFalse(ongoing_event.is_upcoming)
        self.assertTrue(ongoing_event.is_ongoing)

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

        cls.publication_index = PublicationIndexPage.objects.first()

        project1 = ProjectPage(
            title="Urban Project", rubrics=rubrics(RubricCode.HOUSING, RubricCode.HERITAGE)
        )
        cls.publication_index.add_child(instance=project1)
        project1.save_revision().publish()

        project2 = ProjectPage(
            title="Environment Project", rubrics=rubrics(RubricCode.PARKS_GARDENS)
        )
        cls.publication_index.add_child(instance=project2)
        project2.save_revision().publish()

        event = EventPage(title="Future Event", event_date=timezone.now() + timedelta(days=7))
        cls.publication_index.add_child(instance=event)
        event.save_revision().publish()

    def test_get_publications_filters_by_type(self) -> None:
        # Projects or events, never both: projects unless asked otherwise.
        request = self.factory.get("/publications/")
        self.assertEqual(len(self.publication_index.get_publications(request)), 2)

        request = self.factory.get("/publications/?type=all")
        self.assertEqual(len(self.publication_index.get_publications(request)), 2)

        request = self.factory.get("/publications/?type=projects")
        self.assertEqual(len(self.publication_index.get_publications(request)), 2)

        request = self.factory.get("/publications/?type=events")
        self.assertEqual(len(self.publication_index.get_publications(request)), 1)

    def test_get_publications_filters_by_rubric(self) -> None:
        for code in (RubricCode.HOUSING, RubricCode.HERITAGE):
            request = self.factory.get(f"/publications/?type=projects&rubric={code}")
            publications = self.publication_index.get_publications(request)

            self.assertEqual(len(publications), 1)
            self.assertEqual(publications[0].title, "Urban Project")

        request = self.factory.get("/publications/?type=projects&rubric=PUBLIC_SPACE")
        self.assertEqual(len(self.publication_index.get_publications(request)), 0)

    def test_get_publications_ignores_invalid_rubric(self) -> None:
        request = self.factory.get("/publications/?type=projects&rubric=INVALID")
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
            project = ProjectPage(title=f"Project {i}", rubrics=rubrics(RubricCode.PUBLIC_SPACE))
            self.publication_index.add_child(instance=project)
            project.save_revision().publish()

        request = self.factory.get("/publications/?type=projects&page=1")
        self.assertEqual(len(self.publication_index.get_publications(request)), 12)

        request = self.factory.get("/publications/?type=projects&page=2")
        self.assertEqual(len(self.publication_index.get_publications(request)), 5)

    def test_get_publications_invalid_page_falls_back(self) -> None:
        for i in range(15):
            project = ProjectPage(title=f"Project {i}", rubrics=rubrics(RubricCode.PUBLIC_SPACE))
            self.publication_index.add_child(instance=project)
            project.save_revision().publish()

        for page in ("abc", "-1", "999"):
            request = self.factory.get(f"/publications/?type=projects&page={page}")
            self.assertGreater(len(self.publication_index.get_publications(request)), 0)

    def test_index_page_renders_with_invalid_page(self) -> None:
        self.publication_index.save_revision().publish()

        response = self.client.get(self.publication_index.url + "?page=abc")

        self.assertEqual(response.status_code, 200)

    def test_filter_links_keep_other_params_and_encode_values(self) -> None:
        self.publication_index.save_revision().publish()

        response = self.client.get(
            self.publication_index.url + "?type=projects&search=a%26b&rubric=PARKS_GARDENS"
        )

        content = response.content.decode()
        # Rubric links keep the search term, URL-encoded, and drop the page.
        self.assertIn("type=projects&amp;search=a%26b&amp;rubric=HOUSING", content)
        self.assertNotIn("search=a&b", content)

    def test_project_cards_have_no_type_badge(self) -> None:
        self.publication_index.save_revision().publish()

        response = self.client.get(self.publication_index.url)

        self.assertEqual(response.context["selected_type"], "projects")
        self.assertNotContains(response, "badge-primary")

    def test_rubric_filter_offers_all_urban_planning(self) -> None:
        self.publication_index.save_revision().publish()

        response = self.client.get(self.publication_index.url + "?type=projects")

        self.assertContains(response, _("All urban planning"))

    def test_pagination_links_keep_filters(self) -> None:
        for i in range(15):
            project = ProjectPage(title=f"Project {i}", rubrics=rubrics(RubricCode.PUBLIC_SPACE))
            self.publication_index.add_child(instance=project)
            project.save_revision().publish()
        self.publication_index.save_revision().publish()

        response = self.client.get(
            self.publication_index.url + "?type=projects&rubric=PUBLIC_SPACE"
        )

        self.assertIn(
            "?type=projects&amp;rubric=PUBLIC_SPACE&amp;page=2", response.content.decode()
        )

    def test_get_context_returns_expected_keys(self) -> None:
        request = self.factory.get("/publications/?type=events&rubric=HOUSING")
        context = self.publication_index.get_context(request)

        self.assertIn("publications", context)
        self.assertEqual([r.value for r in context["rubrics"]], RubricCode.values)
        self.assertEqual(context["selected_type"], "events")
        self.assertEqual(context["selected_rubric"], "HOUSING")
