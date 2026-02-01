import json

import pytest
from django.test import Client
from django.urls import reverse

from core.models import User
from publications.models import FormResponse, ProjectPage, VoteChoice


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        email="testuser@example.com",
        password="TestPass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def publication_index(db):
    """Create a publication index page."""
    from wagtail.models import Page

    from publications.models import PublicationIndexPage

    root_page = Page.objects.get(depth=1)

    try:
        index_page = PublicationIndexPage.objects.first()
        if not index_page:
            index_page = PublicationIndexPage(
                title="Publications",
                slug="publications",
            )
            root_page.add_child(instance=index_page)
    except Exception:
        index_page = PublicationIndexPage(
            title="Publications",
            slug="publications",
        )
        root_page.add_child(instance=index_page)

    return index_page


@pytest.fixture
def project_with_voting(publication_index):
    """Create a project page with voting enabled."""
    project = ProjectPage(
        title="Test Project",
        slug="test-project",
        enable_voting=True,
    )
    publication_index.add_child(instance=project)

    return project


@pytest.fixture
def closed_project(publication_index):
    """Create a project page with voting closed (past end date)."""
    from datetime import timedelta

    from django.utils import timezone

    project = ProjectPage(
        title="Closed Voting Project",
        slug="closed-voting-project",
        enable_voting=True,
        voting_end_date=timezone.now() - timedelta(days=1),
    )
    publication_index.add_child(instance=project)

    return project


class TestProjectVoting:
    """Tests for project voting functionality."""

    def test_project_with_voting_enabled(self, db):
        """Test creating a project with voting enabled."""
        from wagtail.models import Page
        from publications.models import PublicationIndexPage

        root_page = Page.objects.get(depth=1)
        index_page = PublicationIndexPage(title="Publications", slug="pubs")
        root_page.add_child(instance=index_page)

        project = ProjectPage(
            title="Test Project",
            slug="test-proj",
            enable_voting=True,
        )
        index_page.add_child(instance=project)

        assert project.pk is not None
        assert project.enable_voting is True
        assert project.is_voting_open is True

    def test_project_voting_with_end_date(self, db):
        """Test project with a voting end date."""
        from django.utils import timezone
        from datetime import timedelta
        from wagtail.models import Page
        from publications.models import PublicationIndexPage

        root_page = Page.objects.get(depth=1)
        index_page = PublicationIndexPage(title="Publications", slug="pubs2")
        root_page.add_child(instance=index_page)

        # Project with open voting
        open_project = ProjectPage(
            title="Open Project",
            slug="open-proj",
            enable_voting=True,
            voting_end_date=timezone.now() + timedelta(days=7),
        )
        index_page.add_child(instance=open_project)
        assert open_project.is_voting_open is True

        # Project with closed voting
        closed_project = ProjectPage(
            title="Closed Project",
            slug="closed-proj",
            enable_voting=True,
            voting_end_date=timezone.now() - timedelta(days=1),
        )
        index_page.add_child(instance=closed_project)
        assert closed_project.is_voting_open is False


class TestFormResponseModel:
    """Tests for the FormResponse model."""

    def test_create_form_response(self, db, user, project_with_voting):
        """Test creating a form response."""
        response = FormResponse.objects.create(
            user=user,
            project=project_with_voting,
            choice=VoteChoice.FAVORABLE,
            comment="Great project!",
        )
        assert response.pk is not None
        assert response.choice == VoteChoice.FAVORABLE

    def test_unique_user_project_vote(self, db, user, project_with_voting):
        """Test that a user can only have one vote per project."""
        FormResponse.objects.create(
            user=user,
            project=project_with_voting,
            choice=VoteChoice.FAVORABLE,
        )

        # Attempting to create another response should fail
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            FormResponse.objects.create(
                user=user,
                project=project_with_voting,
                choice=VoteChoice.UNFAVORABLE,
            )


class TestVoteAPI:
    """Tests for the vote API endpoints."""

    def test_vote_requires_authentication(self, client, project_with_voting):
        """Test that voting requires authentication."""
        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps({"choice": "FAVORABLE"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_submit_vote(self, client, user, project_with_voting):
        """Test submitting a vote."""
        client.force_login(user)

        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                    "comment": "I support this project!",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["vote"]["choice"] == "FAVORABLE"
        assert "results" in data

    def test_update_vote(self, client, user, project_with_voting):
        """Test updating an existing vote."""
        client.force_login(user)

        # First vote
        client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps({"choice": "FAVORABLE"}),
            content_type="application/json",
        )

        # Update vote
        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps({"choice": "UNFAVORABLE"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vote"]["choice"] == "UNFAVORABLE"

    def test_delete_vote(self, client, user, project_with_voting):
        """Test removing a vote."""
        client.force_login(user)

        # First, submit a vote
        client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps({"choice": "FAVORABLE"}),
            content_type="application/json",
        )

        # Delete the vote
        response = client.delete(f"/api/projects/{project_with_voting.pk}/vote")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_vote_results_not_voted(self, client, user, project_with_voting):
        """Test getting results when user hasn't voted."""
        client.force_login(user)

        response = client.get(f"/api/projects/{project_with_voting.pk}/vote/results")

        assert response.status_code == 200
        data = response.json()
        assert data["has_voted"] is False
        assert data["results"] is None

    def test_get_vote_results_after_voting(self, client, user, project_with_voting):
        """Test getting results after voting."""
        client.force_login(user)

        # Submit a vote
        client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps({"choice": "FAVORABLE"}),
            content_type="application/json",
        )

        # Get results
        response = client.get(f"/api/projects/{project_with_voting.pk}/vote/results")

        assert response.status_code == 200
        data = response.json()
        assert data["has_voted"] is True
        assert data["results"] is not None
        assert data["results"]["total_votes"] == 1

    def test_invalid_choice(self, client, user, project_with_voting):
        """Test submitting an invalid vote choice."""
        client.force_login(user)

        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps({"choice": "INVALID_CHOICE"}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_vote_on_project_without_voting(self, client, user, publication_index):
        """Test voting on a project without voting enabled."""
        project = ProjectPage(
            title="Project Without Voting",
            slug="project-without-voting",
            enable_voting=False,
        )
        publication_index.add_child(instance=project)

        client.force_login(user)

        response = client.post(
            f"/api/projects/{project.pk}/vote",
            data=json.dumps({"choice": "FAVORABLE"}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_vote_on_closed_project(self, client, user, closed_project):
        """Test voting on a project with voting closed (past end date)."""
        # Verify voting is closed
        assert closed_project.is_voting_open is False

        client.force_login(user)

        response = client.post(
            f"/api/projects/{closed_project.pk}/vote",
            data=json.dumps({"choice": "FAVORABLE"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "message" in data


class TestVoteAnonymization:
    """Tests for vote anonymization functionality."""

    def test_submit_anonymous_vote(self, client, user, project_with_voting):
        """Test submitting an anonymous vote."""
        client.force_login(user)

        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                    "comment": "Anonymous comment",
                    "anonymize": True,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["vote"]["anonymize"] is True

        # Verify in database
        form_response = FormResponse.objects.get(user=user, project=project_with_voting)
        assert form_response.anonymize is True

    def test_submit_non_anonymous_vote(self, client, user, project_with_voting):
        """Test submitting a non-anonymous vote."""
        client.force_login(user)

        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                    "comment": "Public comment",
                    "anonymize": False,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vote"]["anonymize"] is False

        # Verify in database
        form_response = FormResponse.objects.get(user=user, project=project_with_voting)
        assert form_response.anonymize is False

    def test_vote_anonymize_defaults_to_false(self, client, user, project_with_voting):
        """Test that anonymize defaults to False when not provided."""
        client.force_login(user)

        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify in database
        form_response = FormResponse.objects.get(user=user, project=project_with_voting)
        assert form_response.anonymize is False

    def test_update_vote_anonymization(self, client, user, project_with_voting):
        """Test updating vote anonymization status."""
        client.force_login(user)

        # First vote (non-anonymous)
        client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                    "anonymize": False,
                }
            ),
            content_type="application/json",
        )

        # Update to anonymous
        response = client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                    "anonymize": True,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vote"]["anonymize"] is True

        # Verify in database
        form_response = FormResponse.objects.get(user=user, project=project_with_voting)
        assert form_response.anonymize is True

    def test_get_vote_results_includes_anonymize_status(self, client, user, project_with_voting):
        """Test that vote results include anonymization status."""
        client.force_login(user)

        # Submit anonymous vote
        client.post(
            f"/api/projects/{project_with_voting.pk}/vote",
            data=json.dumps(
                {
                    "choice": "FAVORABLE",
                    "anonymize": True,
                }
            ),
            content_type="application/json",
        )

        # Get results
        response = client.get(f"/api/projects/{project_with_voting.pk}/vote/results")

        assert response.status_code == 200
        data = response.json()
        assert data["user_vote"]["anonymize"] is True
