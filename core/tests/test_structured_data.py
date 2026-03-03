import json
from datetime import timedelta

from django.conf import settings
from django.test import RequestFactory, TestCase
from django.utils import timezone
from wagtail.models import Site

from core.templatetags.structured_data import get_structured_data, structured_data_script
from home.models import HomePage
from pedagogy.factories.pedagogy_card_factory import PedagogyCardPageFactory
from pedagogy.models import PedagogyIndexPage, PedagogyCardPage
from publications.factories import EventPageFactory, ProjectPageFactory
from publications.models import PublicationIndexPage, EventPage, ProjectPage
from publications.models.project import ProjectCategory


class StructuredDataBaseTestCase(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

        self.site = Site.objects.get(is_default_site=True)

        self.home = HomePage(title="Accueil", slug="home")
        self.site.root_page.add_child(instance=self.home)
        self.site.root_page = self.home
        self.site.save()

        # Pedagogy index
        self.pedagogy_index = PedagogyIndexPage(
            title="Ressources pédagogiques",
            slug="pedagogy",
            page_introduction="Introduction pédagogique",
        )
        self.home.add_child(instance=self.pedagogy_index)

        # Publication index
        self.publication_index = PublicationIndexPage(
            title="Publications",
            slug="publications",
            page_introduction="Découvrez nos publications",
        )
        self.home.add_child(instance=self.publication_index)


class HomePageStructuredDataTests(StructuredDataBaseTestCase):
    def test_type_is_website(self) -> None:
        schema = get_structured_data(self.request, self.home)
        self.assertEqual(schema["@type"], "WebSite")
        self.assertEqual(schema["@context"], "https://schema.org")

    def test_name_is_site_name(self) -> None:
        schema = get_structured_data(self.request, self.home)
        self.assertEqual(schema["name"], settings.WEBSITE_NAME)

    def test_url_is_present(self) -> None:
        schema = get_structured_data(self.request, self.home)
        self.assertIn("url", schema)

    def test_description_from_search_description(self) -> None:
        self.home.search_description = "La plateforme urbaine participative"
        self.home.save()
        schema = get_structured_data(self.request, self.home)
        self.assertEqual(schema["description"], "La plateforme urbaine participative")

    def test_no_description_when_empty(self) -> None:
        self.home.search_description = ""
        self.home.save()
        schema = get_structured_data(self.request, self.home)
        self.assertNotIn("description", schema)


class PedagogyIndexStructuredDataTests(StructuredDataBaseTestCase):
    def test_type_is_collection_page(self) -> None:
        schema = get_structured_data(self.request, self.pedagogy_index)
        self.assertEqual(schema["@type"], "CollectionPage")

    def test_name_equals_title(self) -> None:
        schema = get_structured_data(self.request, self.pedagogy_index)
        self.assertEqual(schema["name"], self.pedagogy_index.title)

    def test_description_from_page_introduction(self) -> None:
        schema = get_structured_data(self.request, self.pedagogy_index)
        self.assertEqual(schema["description"], "Introduction pédagogique")

    def test_publisher_is_organisation(self) -> None:
        schema = get_structured_data(self.request, self.pedagogy_index)
        self.assertEqual(schema["publisher"]["@type"], "Organization")
        self.assertEqual(schema["publisher"]["name"], settings.WEBSITE_NAME)


class PedagogyCardStructuredDataTests(StructuredDataBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.card: PedagogyCardPage = PedagogyCardPageFactory.create(
            parent=self.home,
            title="Comprendre l'urbanisme",
            description="Une fiche sur l'urbanisme",
        )

    def test_type_is_learning_resource(self) -> None:
        schema = get_structured_data(self.request, self.card)
        self.assertEqual(schema["@type"], "LearningResource")

    def test_name_equals_title(self) -> None:
        schema = get_structured_data(self.request, self.card)
        self.assertEqual(schema["name"], self.card.title)

    def test_description_from_card_description(self) -> None:
        schema = get_structured_data(self.request, self.card)
        self.assertEqual(schema["description"], "Une fiche sur l'urbanisme")

    def test_image_included_when_hero_image_present(self) -> None:
        schema = get_structured_data(self.request, self.card)
        self.assertIn("image", schema)
        self.assertIsInstance(schema["image"], str)

    def test_no_image_when_hero_image_missing(self) -> None:
        self.card.hero_image = None
        schema = get_structured_data(self.request, self.card)
        self.assertNotIn("image", schema)

    def test_date_published_after_publish(self) -> None:
        self.card.first_published_at = timezone.now()
        schema = get_structured_data(self.request, self.card)
        self.assertIn("datePublished", schema)


class PublicationIndexStructuredDataTests(StructuredDataBaseTestCase):
    def test_type_is_collection_page(self) -> None:
        schema = get_structured_data(self.request, self.publication_index)
        self.assertEqual(schema["@type"], "CollectionPage")

    def test_description_from_page_introduction(self) -> None:
        schema = get_structured_data(self.request, self.publication_index)
        self.assertEqual(schema["description"], "Découvrez nos publications")

    def test_publisher_is_organisation(self) -> None:
        schema = get_structured_data(self.request, self.publication_index)
        self.assertEqual(schema["publisher"]["@type"], "Organization")


class ProjectPageStructuredDataTests(StructuredDataBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project: ProjectPage = ProjectPageFactory.create(
            parent=self.home,
            title="Projet de mobilité douce",
            description="Un projet pour améliorer la mobilité",
            category=ProjectCategory.MOBILITY,
        )

    def test_type_is_article(self) -> None:
        schema = get_structured_data(self.request, self.project)
        self.assertEqual(schema["@type"], "Article")

    def test_name_equals_title(self) -> None:
        schema = get_structured_data(self.request, self.project)
        self.assertEqual(schema["name"], self.project.title)

    def test_description_present(self) -> None:
        schema = get_structured_data(self.request, self.project)
        self.assertEqual(schema["description"], "Un projet pour améliorer la mobilité")

    def test_article_section_from_category(self) -> None:
        schema = get_structured_data(self.request, self.project)
        self.assertIn("articleSection", schema)
        self.assertIsInstance(schema["articleSection"], str)
        self.assertNotEqual(schema["articleSection"], "")

    def test_image_included_when_hero_image_present(self) -> None:
        schema = get_structured_data(self.request, self.project)
        self.assertIn("image", schema)

    def test_publisher_is_organisation(self) -> None:
        schema = get_structured_data(self.request, self.project)
        self.assertEqual(schema["publisher"]["@type"], "Organization")
        self.assertEqual(schema["publisher"]["name"], settings.WEBSITE_NAME)


class EventPageStructuredDataTests(StructuredDataBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        now = timezone.now()
        self.event: EventPage = EventPageFactory.create(
            parent=self.home,
            title="Forum de quartier",
            description="Un forum pour les habitants",
            event_date=now + timedelta(days=7),
            end_date=now + timedelta(days=7, hours=3),
            location="Salle des fêtes",
            address="1 rue de la Paix, 75001 Paris",
            is_online=False,
        )

    def test_type_is_event(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertEqual(schema["@type"], "Event")

    def test_name_equals_title(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertEqual(schema["name"], self.event.title)

    def test_description_present(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertEqual(schema["description"], "Un forum pour les habitants")

    def test_start_date_present(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertIn("startDate", schema)

    def test_end_date_present(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertIn("endDate", schema)

    def test_offline_event_has_place_location(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertEqual(schema["location"]["@type"], "Place")
        self.assertEqual(schema["location"]["name"], "Salle des fêtes")
        self.assertEqual(schema["location"]["address"], "1 rue de la Paix, 75001 Paris")

    def test_offline_attendance_mode(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertEqual(
            schema["eventAttendanceMode"],
            "https://schema.org/OfflineEventAttendanceMode",
        )

    def test_online_event_has_virtual_location(self) -> None:
        now = timezone.now()
        online_event: EventPage = EventPageFactory.create(
            parent=self.home,
            event_date=now + timedelta(days=3),
            is_online=True,
            online_link="https://meet.example.com/event",
            location="",
            address="",
        )
        schema = get_structured_data(self.request, online_event)
        self.assertEqual(schema["location"]["@type"], "VirtualLocation")
        self.assertEqual(schema["location"]["url"], "https://meet.example.com/event")
        self.assertEqual(
            schema["eventAttendanceMode"],
            "https://schema.org/OnlineEventAttendanceMode",
        )

    def test_organizer_is_organisation(self) -> None:
        schema = get_structured_data(self.request, self.event)
        self.assertEqual(schema["organizer"]["@type"], "Organization")
        self.assertEqual(schema["organizer"]["name"], settings.WEBSITE_NAME)


class StructuredDataScriptTagTests(StructuredDataBaseTestCase):
    def test_renders_script_tag(self) -> None:
        from django.template import Context

        context = Context({"request": self.request, "page": self.home})
        result = structured_data_script(context)
        self.assertIn('<script type="application/ld+json">', result)
        self.assertIn("</script>", result)

    def test_valid_json_in_script_tag(self) -> None:
        from django.template import Context

        context = Context({"request": self.request, "page": self.home})
        result = str(structured_data_script(context))
        json_str = result.replace('<script type="application/ld+json">', "").replace(
            "</script>", ""
        )
        parsed = json.loads(json_str)
        self.assertEqual(parsed["@type"], "WebSite")

    def test_returns_empty_string_without_page(self) -> None:
        from django.template import Context

        context = Context({"request": self.request})
        result = structured_data_script(context)
        self.assertEqual(str(result), "")

    def test_fallback_for_unknown_page_type(self) -> None:
        schema = get_structured_data(self.request, self.home.get_parent())
        self.assertEqual(schema["@type"], "WebPage")
