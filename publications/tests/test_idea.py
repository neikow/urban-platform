import json

import pytest

from core.models import User
from publications.models import (
    FormResponse,
    IdeaResponse,
    ParticipationMode,
    ProjectPage,
    VoteChoice,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="ideauser@example.com",
        password="TestPass123",
        first_name="Idea",
        last_name="User",
    )


@pytest.fixture
def publication_index(db):
    from wagtail.models import Page

    from publications.models import PublicationIndexPage

    root_page = Page.objects.get(depth=1)
    index_page = PublicationIndexPage.objects.first()
    if not index_page:
        index_page = PublicationIndexPage(title="Publications", slug="publications")
        root_page.add_child(instance=index_page)
    return index_page


@pytest.fixture
def project_with_ideas(publication_index):
    project = ProjectPage(
        title="Idea Project",
        slug="idea-project",
        participation_mode=ParticipationMode.IDEAS,
    )
    publication_index.add_child(instance=project)
    return project


@pytest.fixture
def project_with_voting(publication_index):
    project = ProjectPage(
        title="Voting Project",
        slug="voting-project",
        participation_mode=ParticipationMode.VOTING,
    )
    publication_index.add_child(instance=project)
    return project


class TestParticipationMode:
    def test_ideas_mode_flags(self, project_with_ideas):
        assert project_with_ideas.enable_ideas is True
        assert project_with_ideas.enable_voting is False
        assert project_with_ideas.is_ideas_open is True

    def test_voting_mode_flags(self, project_with_voting):
        assert project_with_voting.enable_voting is True
        assert project_with_voting.enable_ideas is False

    def test_unique_user_project_idea(self, db, user, project_with_ideas):
        IdeaResponse.objects.create(user=user, project=project_with_ideas, description="First idea")
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            IdeaResponse.objects.create(
                user=user, project=project_with_ideas, description="Second idea"
            )


class TestIdeaAPI:
    def test_idea_requires_authentication(self, client, project_with_ideas):
        response = client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "A great idea"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_submit_idea(self, client, user, project_with_ideas):
        client.force_login(user)
        response = client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "Plant more trees along the avenue"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["idea"]["description"] == "Plant more trees along the avenue"
        assert IdeaResponse.objects.filter(user=user, project=project_with_ideas).count() == 1

    def test_update_idea(self, client, user, project_with_ideas):
        client.force_login(user)
        client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "Initial idea"}),
            content_type="application/json",
        )
        response = client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "Revised idea"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["idea"]["description"] == "Revised idea"
        # Still a single response (update, not duplicate).
        assert IdeaResponse.objects.filter(user=user, project=project_with_ideas).count() == 1

    def test_empty_description_rejected(self, client, user, project_with_ideas):
        client.force_login(user)
        response = client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "   "}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_delete_idea(self, client, user, project_with_ideas):
        client.force_login(user)
        client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "Removable idea"}),
            content_type="application/json",
        )
        response = client.delete(f"/api/projects/{project_with_ideas.pk}/idea/")
        assert response.status_code == 200
        assert IdeaResponse.objects.filter(user=user, project=project_with_ideas).count() == 0

    def test_idea_on_voting_project_rejected(self, client, user, project_with_voting):
        client.force_login(user)
        response = client.post(
            f"/api/projects/{project_with_voting.pk}/idea/",
            data=json.dumps({"description": "Idea on a voting project"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_anonymous_idea(self, client, user, project_with_ideas):
        client.force_login(user)
        response = client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "Anonymous idea", "anonymize": True}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["idea"]["anonymize"] is True
        idea = IdeaResponse.objects.get(user=user, project=project_with_ideas)
        assert idea.anonymize is True


class TestIdeaMine:
    def test_mine_before_submission(self, client, user, project_with_ideas):
        client.force_login(user)
        response = client.get(f"/api/projects/{project_with_ideas.pk}/idea/mine/")
        assert response.status_code == 200
        data = response.json()
        assert data["has_submitted"] is False
        assert data["user_idea"] is None

    def test_mine_after_submission(self, client, user, project_with_ideas):
        client.force_login(user)
        client.post(
            f"/api/projects/{project_with_ideas.pk}/idea/",
            data=json.dumps({"description": "My submitted idea"}),
            content_type="application/json",
        )
        response = client.get(f"/api/projects/{project_with_ideas.pk}/idea/mine/")
        assert response.status_code == 200
        data = response.json()
        assert data["has_submitted"] is True
        assert data["user_idea"]["description"] == "My submitted idea"

    def test_mine_on_voting_project_rejected(self, client, user, project_with_voting):
        client.force_login(user)
        response = client.get(f"/api/projects/{project_with_voting.pk}/idea/mine/")
        assert response.status_code == 400


class TestModeSwitchingPreservesResponses:
    """Switching participation mode must never destroy responses already collected."""

    def test_switching_keeps_votes_and_ideas(self, db, user, publication_index):
        project = ProjectPage(
            title="Switching Project",
            slug="switching-project",
            participation_mode=ParticipationMode.VOTING,
        )
        publication_index.add_child(instance=project)

        FormResponse.objects.create(
            user=user, project=project, choice=VoteChoice.FAVORABLE, comment="Nice"
        )

        # Switch to ideas: the vote survives, and a new idea can be added.
        project.participation_mode = ParticipationMode.IDEAS
        project.save()
        IdeaResponse.objects.create(user=user, project=project, description="An idea")

        assert FormResponse.objects.filter(project=project).count() == 1
        assert IdeaResponse.objects.filter(project=project).count() == 1

        # Switch back to voting: both response sets remain intact.
        project.participation_mode = ParticipationMode.VOTING
        project.save()

        assert FormResponse.objects.filter(project=project).count() == 1
        assert IdeaResponse.objects.filter(project=project).count() == 1
