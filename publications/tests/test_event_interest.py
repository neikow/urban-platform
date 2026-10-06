from datetime import timedelta

import pytest
from django.utils import timezone

from core.models import User
from home.models import HomePage
from publications.models import EventInterest, EventPage, PublicationIndexPage


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


@pytest.fixture
def resident(db):
    return User.objects.create_user(
        email="resident@example.com", password="x", first_name="R", last_name="S", is_verified=True
    )


def interest_url(event):
    return f"/api/events/{event.pk}/interest/"


@pytest.mark.django_db
class TestEventInterest:
    def test_anonymous_can_read_the_counter(self, client, index):
        event = make_event(index)

        data = client.get(interest_url(event)).json()

        assert data == {"success": True, "interested": False, "count": 0}

    def test_anonymous_cannot_flag(self, client, index):
        response = client.post(interest_url(make_event(index)))

        assert response.status_code == 401

    def test_unverified_user_cannot_flag(self, client, index):
        user = User.objects.create_user(
            email="u@example.com", password="x", first_name="U", last_name="V"
        )
        client.force_login(user)

        response = client.post(interest_url(make_event(index)))

        assert response.status_code == 403
        assert response.json()["code"] == "email_not_verified"

    def test_flag_and_unflag(self, client, index, resident):
        event = make_event(index)
        client.force_login(resident)

        added = client.post(interest_url(event)).json()
        again = client.post(interest_url(event)).json()
        removed = client.delete(interest_url(event)).json()

        assert (added["interested"], added["count"]) == (True, 1)
        assert again["count"] == 1  # idempotent
        assert (removed["interested"], removed["count"]) == (False, 0)

    def test_no_code_of_conduct_needed(self, client, index, resident):
        # The data migration publishes a code of conduct; the resident never accepted it.
        client.force_login(resident)

        assert client.post(interest_url(make_event(index))).status_code == 200

    def test_past_event_refuses_new_interest(self, client, index, resident):
        client.force_login(resident)

        response = client.post(interest_url(make_event(index, days=-3)))

        assert response.status_code == 400

    def test_unpublished_event_is_not_found(self, client, index, resident):
        event = make_event(index)
        event.unpublish()
        client.force_login(resident)

        assert client.post(interest_url(event)).status_code == 404

    def test_event_page_renders_state(self, client, index, resident):
        event = make_event(index)
        EventInterest.objects.create(user=resident, event=event)
        client.force_login(resident)

        content = client.get(event.url).content.decode()

        assert 'aria-pressed="true"' in content
        assert "1 personne intéressée" in content or "1 person is interested" in content
        assert "dist/event-interest.js" in content


@pytest.mark.django_db
def test_profile_lists_upcoming_interesting_events(client, index, resident):
    upcoming = make_event(index, slug="soon", title="Bientôt")
    past = make_event(index, slug="past", title="Passé", days=-3)
    EventInterest.objects.create(user=resident, event=upcoming)
    EventInterest.objects.create(user=resident, event=past)
    client.force_login(resident)

    response = client.get("/auth/me/")

    assert [e.title for e in response.context["interesting_events"]] == ["Bientôt"]
