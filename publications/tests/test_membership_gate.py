import json

import pytest

from datetime import timedelta

from django.utils import timezone

from core.models import FeatureFlags, Membership, User
from publications.models import EventInterest
from publications.tests.test_event_interest import make_event
from publications.tests.test_participation_guards import make_user, post_idea, post_vote


@pytest.fixture
def reserved(db):
    flags = FeatureFlags.load()
    flags.participation_requires_membership = True
    flags.save()
    return flags


@pytest.fixture
def resident(db, give_code_of_conduct_consent):
    user = make_user("resident@example.com", is_verified=True)
    give_code_of_conduct_consent(user)
    return user


@pytest.fixture
def member(db, give_code_of_conduct_consent):
    user = make_user("member@example.com", is_verified=True)
    Membership.objects.create(user=user)
    give_code_of_conduct_consent(user)
    return user


@pytest.mark.django_db
class TestMembershipGate:
    def test_open_to_everyone_by_default(self, client, resident, voting_project, ideas_project):
        client.force_login(resident)

        assert post_vote(client, voting_project).status_code == 200
        assert post_idea(client, ideas_project).status_code in (200, 201)

    def test_reserved_refuses_other_users(
        self, client, reserved, resident, voting_project, ideas_project
    ):
        client.force_login(resident)

        for response in (post_vote(client, voting_project), post_idea(client, ideas_project)):
            assert response.status_code == 403
            assert response.json()["code"] == "membership_required"

    def test_reserved_accepts_members(
        self, client, reserved, member, voting_project, ideas_project
    ):
        client.force_login(member)

        assert post_vote(client, voting_project).status_code == 200
        assert post_idea(client, ideas_project).status_code in (200, 201)

    def test_staff_need_a_membership_too(self, client, reserved, resident, voting_project):
        User.objects.filter(pk=resident.pk).update(role="MODERATOR")
        client.force_login(resident)

        assert post_vote(client, voting_project).status_code == 403

    def test_event_interest_stays_open(self, client, reserved, resident, publication_index):
        event = make_event(publication_index)
        client.force_login(resident)

        response = client.post(f"/api/events/{event.pk}/interest/")

        assert response.status_code == 200
        assert EventInterest.objects.filter(user=resident, event=event).exists()


@pytest.mark.django_db
class TestProjectPage:
    def page(self, client, project):
        project.save_revision().publish()
        return client.get(project.url).content.decode()

    def test_prompt_instead_of_the_form(self, client, reserved, resident, voting_project):
        client.force_login(resident)

        content = self.page(client, voting_project)

        assert 'data-can-participate="false"' in content
        assert 'id="vote-form"' not in content

    def test_form_for_members(self, client, reserved, member, voting_project):
        client.force_login(member)

        content = self.page(client, voting_project)

        assert 'data-can-participate="true"' in content
        assert 'id="vote-form"' in content


@pytest.mark.django_db
def test_only_a_running_membership_counts(client, reserved, resident, voting_project):
    today = timezone.localdate()
    Membership.objects.create(
        user=resident, starts_on=today - timedelta(days=400), ends_on=today - timedelta(days=35)
    )
    Membership.objects.create(user=resident, starts_on=today + timedelta(days=3))
    client.force_login(resident)

    assert post_vote(client, voting_project).status_code == 403
