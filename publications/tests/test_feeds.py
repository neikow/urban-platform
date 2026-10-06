from datetime import timedelta
from xml.etree import ElementTree

import pytest
from django.utils import timezone

from home.models import HomePage
from publications.ical import escape_text, fold
from publications.models import EventPage, ProjectPage, PublicationIndexPage


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


def make_event(index, slug="fete", days=3, **kwargs) -> EventPage:
    start = timezone.now() + timedelta(days=days)
    event = EventPage(
        title=kwargs.pop("title", "Fête du quartier"),
        slug=slug,
        event_date=start,
        end_date=start + timedelta(hours=2),
        location="Place Saint-Eugène",
        address="1 rue d'Endoume\n13007 Marseille",
        description="Musique, jeux; buvette, grillades",
        **kwargs,
    )
    index.add_child(instance=event)
    event.save_revision().publish()
    return event


class TestIcalHelpers:
    def test_escape_text(self):
        assert escape_text("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"

    def test_fold_long_lines_on_octets(self):
        line = "SUMMARY:" + "é" * 60  # 8 + 120 octets
        folded = fold(line)

        parts = folded.split("\r\n")
        assert all(len(part.encode()) <= 75 for part in parts)
        assert all(part.startswith(" ") for part in parts[1:])
        assert "".join(p[1:] if i else p for i, p in enumerate(parts)) == line

    def test_short_lines_untouched(self):
        assert fold("SUMMARY:x") == "SUMMARY:x"


@pytest.mark.django_db
class TestCalendars:
    def test_single_event_download(self, client, index):
        event = make_event(index)

        response = client.get(f"/evenements/{event.pk}/agenda.ics")

        assert response["Content-Type"] == "text/calendar; charset=utf-8"
        assert "attachment" in response["Content-Disposition"]
        body = response.content.decode()
        assert body.startswith("BEGIN:VCALENDAR\r\n")
        assert body.endswith("END:VCALENDAR\r\n")
        unfolded = body.replace("\r\n ", "")
        assert f"UID:event-{event.pk}@testserver" in unfolded
        assert "SUMMARY:Fête du quartier" in unfolded
        assert "LOCATION:Place Saint-Eugène\\, 1 rue d'Endoume\\, 13007 Marseille" in unfolded
        assert "DESCRIPTION:Musique\\, jeux\\; buvette\\, grillades" in unfolded
        assert (
            f"DTSTART:{event.event_date.astimezone(timezone.UTC).strftime('%Y%m%dT%H%M%SZ')}"
            in unfolded
        )

    def test_draft_event_not_downloadable(self, client, index):
        event = make_event(index)
        event.unpublish()

        assert client.get(f"/evenements/{event.pk}/agenda.ics").status_code == 404

    def test_feed_keeps_recent_and_upcoming_events(self, client, index):
        make_event(index, slug="soon", title="Bientôt", days=5)
        make_event(index, slug="recent", title="Récent", days=-10)
        make_event(index, slug="old", title="Ancien", days=-200)

        body = client.get("/feeds/evenements.ics").content.decode()

        assert body.count("BEGIN:VEVENT") == 2
        assert "Ancien" not in body


@pytest.mark.django_db
def test_rss_feed_lists_publications(client, index):
    make_event(index)
    project = ProjectPage(title="Jardin", slug="jardin", description="Un jardin partagé")
    index.add_child(instance=project)
    project.save_revision().publish()

    response = client.get("/feeds/actualites.rss")

    assert response["Content-Type"].startswith("application/rss+xml")
    channel = ElementTree.fromstring(response.content).find("channel")
    titles = [item.findtext("title") for item in channel.findall("item")]
    assert set(titles) == {"Jardin", "Fête du quartier"}
    jardin = next(i for i in channel.findall("item") if i.findtext("title") == "Jardin")
    assert jardin.findtext("link").endswith("/jardin/")
    assert jardin.findtext("description") == "Un jardin partagé"


@pytest.mark.django_db
def test_rss_is_advertised_in_head(client, index):
    content = client.get(index.url).content.decode()

    assert 'type="application/rss+xml"' in content
    assert "webcal://testserver/feeds/evenements.ics" in content
