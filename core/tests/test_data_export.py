import json
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone

from core.data_export import EXCLUDED_RELATIONS, export_user_data
from core.models import EmailEvent, EmailEventStatus, EmailEventType, User
from home.models import HomePage
from publications.models import (
    EventInterest,
    EventPage,
    FormResponse,
    IdeaResponse,
    ParticipationMode,
    ProjectPage,
    PublicationIndexPage,
    VoteChoice,
)

# Relations the export covers explicitly (see core.data_export).
COVERED_RELATIONS = {
    "core.EmailEvent",
    "core.Membership",
    "core.NeighborhoodAssociation",
    "legal.CodeOfConductConsent",
    "publications.EventInterest",
    "publications.FormResponse",
    "publications.IdeaResponse",
    "wagtailcore.Comment",
    "wagtailcore.APIToken",
}


def test_every_relation_to_user_is_exported_or_excluded_on_purpose():
    """Adding a model with a FK to User must update the export (or say why not)."""
    related = {rel.related_model._meta.label for rel in User._meta.related_objects}

    assert related - COVERED_RELATIONS - set(EXCLUDED_RELATIONS) == set()


@pytest.fixture
def resident(db, give_code_of_conduct_consent):
    user = User.objects.create_user(
        email="resident@example.com",
        password="x",
        first_name="Rosa",
        last_name="Martin",
        postal_code="13007",
        is_verified=True,
        notify_event_reminders=True,
    )
    user.set_newsletter_subscription(True)
    user.save()
    give_code_of_conduct_consent(user)
    return user


@pytest.fixture
def activity(resident):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
    vote_project = ProjectPage(
        title="Jardin", slug="jardin", participation_mode=ParticipationMode.VOTING
    )
    idea_project = ProjectPage(
        title="Place", slug="place", participation_mode=ParticipationMode.IDEAS
    )
    event = EventPage(title="Fête", slug="fete", event_date=timezone.now())
    for page in (vote_project, idea_project, event):
        index.add_child(instance=page)
        page.save_revision().publish()
    FormResponse.objects.create(
        user=resident, project=vote_project, choice=VoteChoice.FAVORABLE, comment="Oui !"
    )
    IdeaResponse.objects.create(user=resident, project=idea_project, description="Des bancs")
    EventInterest.objects.create(user=resident, event=event)
    EmailEvent.objects.create(
        user=resident,
        event_type=EmailEventType.VERIFICATION,
        status=EmailEventStatus.SENT,
        recipient_email=resident.email,
    )


@pytest.mark.django_db
def test_export_contains_all_personal_data(resident, activity):
    data = export_user_data(resident)

    assert data["account"]["email"] == "resident@example.com"
    assert data["account"]["newsletter"]["consent_given_at"] is not None
    assert data["account"]["email_notifications"]["event_reminders"] is True
    assert data["participation"]["votes"][0]["comment"] == "Oui !"
    assert data["participation"]["votes"][0]["project_url"].endswith("/jardin/")
    assert data["participation"]["ideas"][0]["idea"] == "Des bancs"
    assert data["participation"]["events_of_interest"][0]["event"] == "Fête"
    assert len(data["code_of_conduct_consents"]) == 1
    assert data["emails_sent"][0]["recipient"] == "resident@example.com"
    assert "editorial_activity" not in data


@pytest.mark.django_db
def test_editors_also_get_their_editorial_activity(db):
    admin = User.objects.create_superuser(
        email="ed@example.com", password="x", first_name="E", last_name="D"
    )

    assert "editorial_activity" in export_user_data(admin)


@pytest.mark.django_db
def test_download_requires_login(client):
    response = client.get(reverse("data_export"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_download_is_a_json_attachment_of_my_own_data(client, resident, activity):
    other = User.objects.create_user(
        email="other@example.com", password="x", first_name="O", last_name="P"
    )
    client.force_login(resident)

    response = client.get(reverse("data_export"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert response["Content-Disposition"].startswith('attachment; filename="mes-donnees-')
    assert response["Cache-Control"] == "no-store"
    data = json.loads(response.content)
    assert data["account"]["email"] == resident.email
    assert other.email not in response.content.decode()


@pytest.mark.django_db
def test_download_is_rate_limited(client, resident):
    client.force_login(resident)

    with mock.patch("django_ratelimit.decorators.is_ratelimited", return_value=True):
        response = client.get(reverse("data_export"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_links_to_the_export(client, resident):
    client.force_login(resident)

    assert reverse("data_export") in client.get(reverse("me")).content.decode()
