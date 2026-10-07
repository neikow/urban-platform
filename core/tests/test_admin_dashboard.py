from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.html import escape

from core.models import User, UserRole
from home.models import HomePage
from publications.models import (
    EventInterest,
    EventPage,
    FormResponse,
    ParticipationMode,
    ProjectPage,
    PublicationIndexPage,
    VoteChoice,
)


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="root@example.com", password="pass12345")


def dashboard(client, user):
    client.force_login(user)
    response = client.get("/admin/")
    assert response.status_code == 200
    return response.content.decode()


@pytest.mark.django_db
class TestDashboard:
    def test_quick_actions(self, client, superuser, index):
        content = dashboard(client, superuser)

        assert 'id="quick-actions-section"' in content
        assert f"/admin/pages/add/publications/projectpage/{index.pk}/" in content
        assert "/admin/settings/core/announcement/" in content

    def test_members_without_page_rights_only_get_the_announcement(self, client, index):
        member = User.objects.create_user(
            email="member@example.com", password="pass12345", role=UserRole.ASSOCIATION_MEMBER
        )

        content = dashboard(client, member)

        assert "/admin/settings/core/announcement/" in content
        assert "/admin/pages/add/" not in content

    def test_consultations_with_their_responses(self, client, superuser, index):
        project = ProjectPage(
            title="Jardin partagé",
            slug="jardin",
            participation_mode=ParticipationMode.VOTING,
            voting_end_date=timezone.now() + timedelta(days=5),
        )
        index.add_child(instance=project)
        project.save_revision().publish()
        FormResponse.objects.create(user=superuser, project=project, choice=VoteChoice.FAVORABLE)

        content = dashboard(client, superuser)

        assert "Jardin partagé" in content
        assert f"/admin/vote-statistics/{project.pk}/" in content
        assert "<td>1</td>" in content

    def test_upcoming_events_with_interest(self, client, superuser, index):
        start = timezone.now() + timedelta(days=3)
        event = EventPage(title="Balade du Roucas", slug="balade", event_date=start, end_date=start)
        index.add_child(instance=event)
        event.save_revision().publish()
        EventInterest.objects.create(user=superuser, event=event)

        content = dashboard(client, superuser)

        assert "Balade du Roucas" in content
        assert "<td>1</td>" in content

    def test_drafts_waiting(self, client, superuser, index):
        draft = ProjectPage(title="Projet en préparation", slug="brouillon", live=False)
        index.add_child(instance=draft)
        draft.save_revision(user=superuser)

        content = dashboard(client, superuser)

        assert 'id="drafts-section"' in content
        assert escape("Projet en préparation") in content

    def test_drafts_are_limited_to_pages_the_user_can_edit(self, client, index):
        draft = ProjectPage(title="Projet confidentiel", slug="confidentiel", live=False)
        index.add_child(instance=draft)
        draft.save_revision()
        member = User.objects.create_user(
            email="member@example.com", password="pass12345", role=UserRole.ASSOCIATION_MEMBER
        )

        assert "Projet confidentiel" not in dashboard(client, member)
