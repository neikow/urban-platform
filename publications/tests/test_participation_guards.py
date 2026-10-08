import json
from unittest import mock

import pytest
from wagtail.models import Page

from core.models import User
from publications.models import (
    FormResponse,
    IdeaResponse,
    ParticipationMode,
    ProjectPage,
    PublicationIndexPage,
)
from publications.models.form import VOTE_COMMENT_MAX_LENGTH
from publications.models.idea import IDEA_MAX_LENGTH


def make_user(email: str, **kwargs) -> User:
    return User.objects.create_user(
        email=email, password="TestPass123", first_name="A", last_name="B", **kwargs
    )


@pytest.fixture
def participant(db, give_code_of_conduct_consent):
    user = make_user("participant@example.com", is_verified=True)
    give_code_of_conduct_consent(user)
    return user


def post_vote(client, project, **payload):
    payload.setdefault("choice", "FAVORABLE")
    return client.post(
        f"/api/projects/{project.pk}/vote/",
        data=json.dumps(payload),
        content_type="application/json",
    )


def post_idea(client, project, **payload):
    payload.setdefault("description", "A bench under the plane trees")
    return client.post(
        f"/api/projects/{project.pk}/idea/",
        data=json.dumps(payload),
        content_type="application/json",
    )


@pytest.mark.django_db
class TestOnlyLiveProjects:
    def test_cannot_vote_on_unpublished_project(self, client, participant, voting_project):
        voting_project.unpublish()
        client.force_login(participant)

        response = post_vote(client, voting_project)

        assert response.status_code == 404
        assert not FormResponse.objects.exists()

    def test_cannot_submit_idea_on_unpublished_project(self, client, participant, ideas_project):
        ideas_project.unpublish()
        client.force_login(participant)

        response = post_idea(client, ideas_project)

        assert response.status_code == 404
        assert not IdeaResponse.objects.exists()

    def test_results_hidden_for_unpublished_project(self, client, voting_project):
        voting_project.unpublish()

        response = client.get(f"/api/projects/{voting_project.pk}/vote/results/")

        assert response.status_code == 404


@pytest.mark.django_db
class TestEmailVerificationRequired:
    def test_unverified_user_cannot_vote(
        self, client, voting_project, give_code_of_conduct_consent
    ):
        user = make_user("unverified@example.com")
        give_code_of_conduct_consent(user)
        client.force_login(user)

        response = post_vote(client, voting_project)

        assert response.status_code == 403
        assert response.json()["code"] == "email_not_verified"
        assert not FormResponse.objects.exists()

    def test_unverified_user_cannot_submit_idea(
        self, client, ideas_project, give_code_of_conduct_consent
    ):
        user = make_user("unverified@example.com")
        give_code_of_conduct_consent(user)
        client.force_login(user)

        response = post_idea(client, ideas_project)

        assert response.status_code == 403
        assert response.json()["code"] == "email_not_verified"

    def test_unverified_user_can_still_read_results(self, client, voting_project):
        client.force_login(make_user("unverified@example.com"))

        response = client.get(f"/api/projects/{voting_project.pk}/vote/results/")

        assert response.status_code == 200


@pytest.mark.django_db
class TestCodeOfConductRequired:
    def test_vote_requires_consent(self, client, voting_project):
        client.force_login(make_user("noconsent@example.com", is_verified=True))

        response = post_vote(client, voting_project)

        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "code_of_conduct_required"
        assert data["action_url"].startswith("/user/code-of-conduct-consent/")

    def test_outdated_consent_is_refused(self, client, participant, voting_project):
        from legal.models import CodeOfConductPage

        CodeOfConductPage.objects.live().first().save_revision()
        client.force_login(participant)

        response = post_vote(client, voting_project)

        assert response.status_code == 403
        assert response.json()["code"] == "code_of_conduct_required"

    def test_no_consent_needed_without_published_code_of_conduct(self, client, voting_project):
        from legal.models import CodeOfConductPage

        for page in CodeOfConductPage.objects.live():
            page.unpublish()
        client.force_login(make_user("noconsent@example.com", is_verified=True))

        response = post_vote(client, voting_project)

        assert response.status_code == 200


@pytest.mark.django_db
class TestLengthLimits:
    def test_vote_comment_too_long(self, client, participant, voting_project):
        client.force_login(participant)

        response = post_vote(client, voting_project, comment="x" * (VOTE_COMMENT_MAX_LENGTH + 1))

        assert response.status_code == 400
        assert not FormResponse.objects.exists()

    def test_vote_comment_at_limit(self, client, participant, voting_project):
        client.force_login(participant)

        response = post_vote(client, voting_project, comment="x" * VOTE_COMMENT_MAX_LENGTH)

        assert response.status_code == 200

    def test_idea_too_long(self, client, participant, ideas_project):
        client.force_login(participant)

        response = post_idea(client, ideas_project, description="x" * (IDEA_MAX_LENGTH + 1))

        assert response.status_code == 400
        assert not IdeaResponse.objects.exists()

    def test_non_string_comment_is_coerced(self, client, participant, voting_project):
        client.force_login(participant)

        response = post_vote(client, voting_project, comment=123)

        assert response.status_code == 200
        assert FormResponse.objects.get().comment == "123"


@pytest.mark.django_db
class TestRateLimit:
    def test_rate_limited_vote_is_refused(self, client, participant, voting_project):
        client.force_login(participant)

        with mock.patch("publications.views.mixins.is_ratelimited", return_value=True):
            response = post_vote(client, voting_project)

        assert response.status_code == 429
        assert not FormResponse.objects.exists()
