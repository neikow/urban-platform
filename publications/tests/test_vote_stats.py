import pytest

from core.models import User
from publications.models import FormResponse, ProjectPage, PublicationIndexPage, VoteChoice
from publications.models.form import FAVORABLE_VALUES, UNFAVORABLE_VALUES


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
def regular_user(db):
    """Create a regular user."""
    return User.objects.create_user(
        email="user@example.com",
        password="UserPass123",
        first_name="Regular",
        last_name="User",
    )


@pytest.fixture
def project_with_votes(db, regular_user):
    """Create a project with some votes."""
    from wagtail.models import Page

    root_page = Page.objects.get(depth=1)

    # Create publication index if needed
    index_page = PublicationIndexPage.objects.first()
    if not index_page:
        index_page = PublicationIndexPage(
            title="Publications",
            slug="publications",
        )
        root_page.add_child(instance=index_page)

    # Create project with voting enabled
    project = ProjectPage(
        title="Test Project with Votes",
        slug="test-project-votes",
        enable_voting=True,
    )
    index_page.add_child(instance=project)

    # Add some votes
    FormResponse.objects.create(
        user=regular_user,
        project=project,
        choice=VoteChoice.FAVORABLE,
        comment="Great project!",
    )

    return project


@pytest.fixture
def project_without_votes(db):
    """Create a project without votes."""
    from wagtail.models import Page

    root_page = Page.objects.get(depth=1)

    index_page = PublicationIndexPage.objects.first()
    if not index_page:
        index_page = PublicationIndexPage(
            title="Publications",
            slug="publications-no-votes",
        )
        root_page.add_child(instance=index_page)

    project = ProjectPage(
        title="Empty Project",
        slug="empty-project",
        enable_voting=True,
    )
    index_page.add_child(instance=project)

    return project


@pytest.mark.django_db
class TestVoteStatsView:
    """Tests for the VoteStatsView admin view."""

    def test_requires_admin_authentication(self, client):
        """Test that the view requires admin authentication."""
        response = client.get("/admin/vote-statistics/")
        assert response.status_code == 302
        assert "/admin/login/" in response.url

    def test_accessible_by_admin(self, client, admin_user, project_with_votes):
        """Test that admin users can access the view."""
        client.force_login(admin_user)
        response = client.get("/admin/vote-statistics/")
        assert response.status_code == 200

    def test_displays_projects_with_voting_enabled(self, client, admin_user, project_with_votes):
        """Test that projects with voting enabled are displayed."""
        client.force_login(admin_user)
        response = client.get("/admin/vote-statistics/")
        assert response.status_code == 200
        assert b"Test Project with Votes" in response.content

    def test_shows_vote_statistics(self, client, admin_user, project_with_votes):
        """Test that vote statistics are shown correctly."""
        client.force_login(admin_user)
        response = client.get("/admin/vote-statistics/")
        assert response.status_code == 200
        # Check that vote count is displayed
        content = response.content.decode()
        assert "1" in content  # 1 vote

    def test_empty_state_when_no_projects(self, client, admin_user, db):
        """Test empty state message when no projects have voting enabled."""
        # Delete all projects with voting
        ProjectPage.objects.filter(enable_voting=True).delete()

        client.force_login(admin_user)
        response = client.get("/admin/vote-statistics/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestVoteStatsDetailView:
    """Tests for the VoteStatsDetailView admin view."""

    def test_requires_admin_authentication(self, client, project_with_votes):
        """Test that the view requires admin authentication."""
        response = client.get(f"/admin/vote-statistics/{project_with_votes.pk}/")
        assert response.status_code == 302
        assert "/admin/login/" in response.url

    def test_accessible_by_admin(self, client, admin_user, project_with_votes):
        """Test that admin users can access the view."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_with_votes.pk}/")
        assert response.status_code == 200

    def test_displays_project_title(self, client, admin_user, project_with_votes):
        """Test that the project title is displayed."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_with_votes.pk}/")
        assert response.status_code == 200
        assert b"Test Project with Votes" in response.content

    def test_displays_vote_breakdown(self, client, admin_user, project_with_votes):
        """Test that vote breakdown is displayed."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_with_votes.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        # Check for vote choice labels
        assert "Favorable" in content

    def test_displays_comments(self, client, admin_user, project_with_votes):
        """Test that comments are displayed."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_with_votes.pk}/")
        assert response.status_code == 200
        assert b"Great project!" in response.content

    def test_returns_404_for_nonexistent_project(self, client, admin_user, db):
        """Test that 404 is returned for nonexistent project."""
        client.force_login(admin_user)
        response = client.get("/admin/vote-statistics/99999/")
        assert response.status_code == 404

    def test_project_without_votes_shows_empty_state(
        self, client, admin_user, project_without_votes
    ):
        """Test that empty state is shown when project has no votes."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_without_votes.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "0" in content or "No votes" in content or "Aucun vote" in content

    def test_anonymous_vote_hides_email_in_admin(self, client, admin_user, project_without_votes):
        """Test that anonymous votes hide user email in admin view."""
        # Create a user who votes anonymously
        anon_voter = User.objects.create_user(
            email="anonymous_voter@example.com",
            password="TestPass123",
            first_name="Anonymous",
            last_name="Voter",
        )

        # Create anonymous vote with comment
        FormResponse.objects.create(
            user=anon_voter,
            project=project_without_votes,
            choice=VoteChoice.FAVORABLE,
            comment="This is an anonymous comment",
            anonymize=True,
        )

        # Access admin stats detail page
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_without_votes.pk}/")

        assert response.status_code == 200
        content = response.content.decode()

        # The comment should be visible
        assert "This is an anonymous comment" in content
        # The email should NOT be visible
        assert "anonymous_voter@example.com" not in content
        # "Anonymous" or "Anonyme" should be displayed instead
        assert "Anonymous" in content or "Anonyme" in content

    def test_non_anonymous_vote_shows_email_in_admin(
        self, client, admin_user, project_without_votes
    ):
        """Test that non-anonymous votes show user email in admin view."""
        # Create a user who votes publicly
        public_voter = User.objects.create_user(
            email="public_voter@example.com",
            password="TestPass123",
            first_name="Public",
            last_name="Voter",
        )

        # Create non-anonymous vote with comment
        FormResponse.objects.create(
            user=public_voter,
            project=project_without_votes,
            choice=VoteChoice.UNFAVORABLE,
            comment="This is a public comment",
            anonymize=False,
        )

        # Access admin stats detail page
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_without_votes.pk}/")

        assert response.status_code == 200
        content = response.content.decode()

        # Both the comment and email should be visible
        assert "This is a public comment" in content
        assert "public_voter@example.com" in content


@pytest.fixture
def project_with_mixed_votes(db):
    """Create a project with a mix of favorable and unfavorable votes for testing aggregates."""
    from wagtail.models import Page

    root_page = Page.objects.get(depth=1)

    index_page = PublicationIndexPage.objects.first()
    if not index_page:
        index_page = PublicationIndexPage(
            title="Publications",
            slug="publications-mixed",
        )
        root_page.add_child(instance=index_page)

    project = ProjectPage(
        title="Mixed Votes Project",
        slug="mixed-votes-project",
        enable_voting=True,
    )
    index_page.add_child(instance=project)

    # Create users and votes with known distribution:
    # 2 FAVORABLE, 1 RATHER_FAVORABLE, 1 RATHER_UNFAVORABLE, 1 UNFAVORABLE
    # Total: 5 votes, 3 favorable (60%), 2 unfavorable (40%)
    users_votes = [
        ("user1@example.com", VoteChoice.FAVORABLE),
        ("user2@example.com", VoteChoice.FAVORABLE),
        ("user3@example.com", VoteChoice.RATHER_FAVORABLE),
        ("user4@example.com", VoteChoice.RATHER_UNFAVORABLE),
        ("user5@example.com", VoteChoice.UNFAVORABLE),
    ]

    for email, choice in users_votes:
        user = User.objects.create_user(
            email=email,
            password="TestPass123",
            first_name=email.split("@")[0],
            last_name="Tester",
        )
        FormResponse.objects.create(
            user=user,
            project=project,
            choice=choice,
        )

    return project


@pytest.mark.django_db
class TestVoteStatsDetailViewAggregates:
    """Tests for favorable/unfavorable totals and percentages in VoteStatsDetailView."""

    def test_favorable_unfavorable_totals(self, client, admin_user, project_with_mixed_votes):
        """Test that favorable and unfavorable totals are correctly calculated."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_with_mixed_votes.pk}/")

        assert response.status_code == 200
        context = response.context

        # 2 FAVORABLE + 1 RATHER_FAVORABLE = 3 favorable
        assert context["favorable_total"] == 3
        # 1 RATHER_UNFAVORABLE + 1 UNFAVORABLE = 2 unfavorable
        assert context["unfavorable_total"] == 2

    def test_favorable_unfavorable_percentages(self, client, admin_user, project_with_mixed_votes):
        """Test that favorable and unfavorable percentages are correctly calculated."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_with_mixed_votes.pk}/")

        assert response.status_code == 200
        context = response.context

        # 3/5 = 60.0%
        assert context["favorable_percentage"] == 60.0
        # 2/5 = 40.0%
        assert context["unfavorable_percentage"] == 40.0

    def test_percentages_rounding(self, client, admin_user, db):
        """Test that percentages are correctly rounded to one decimal place."""
        from wagtail.models import Page

        root_page = Page.objects.get(depth=1)

        index_page = PublicationIndexPage.objects.first()
        if not index_page:
            index_page = PublicationIndexPage(
                title="Publications",
                slug="publications-rounding",
            )
            root_page.add_child(instance=index_page)

        project = ProjectPage(
            title="Rounding Test Project",
            slug="rounding-test-project",
            enable_voting=True,
        )
        index_page.add_child(instance=project)

        # Create 3 votes: 1 favorable, 2 unfavorable
        # favorable: 1/3 = 33.333...% -> should round to 33.3%
        # unfavorable: 2/3 = 66.666...% -> should round to 66.7%
        users_votes = [
            ("rounding1@example.com", VoteChoice.FAVORABLE),
            ("rounding2@example.com", VoteChoice.UNFAVORABLE),
            ("rounding3@example.com", VoteChoice.UNFAVORABLE),
        ]

        for email, choice in users_votes:
            user = User.objects.create_user(
                email=email,
                password="TestPass123",
                first_name=email.split("@")[0],
                last_name="Tester",
            )
            FormResponse.objects.create(
                user=user,
                project=project,
                choice=choice,
            )

        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project.pk}/")

        assert response.status_code == 200
        context = response.context

        assert context["favorable_percentage"] == 33.3
        assert context["unfavorable_percentage"] == 66.7

    def test_zero_votes_percentages(self, client, admin_user, project_without_votes):
        """Test that percentages are 0 when there are no votes (no division by zero)."""
        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project_without_votes.pk}/")

        assert response.status_code == 200
        context = response.context

        assert context["favorable_total"] == 0
        assert context["unfavorable_total"] == 0
        assert context["favorable_percentage"] == 0
        assert context["unfavorable_percentage"] == 0

    def test_all_favorable_votes(self, client, admin_user, db):
        """Test percentages when all votes are favorable."""
        from wagtail.models import Page

        root_page = Page.objects.get(depth=1)

        index_page = PublicationIndexPage.objects.first()
        if not index_page:
            index_page = PublicationIndexPage(
                title="Publications",
                slug="publications-all-favorable",
            )
            root_page.add_child(instance=index_page)

        project = ProjectPage(
            title="All Favorable Project",
            slug="all-favorable-project",
            enable_voting=True,
        )
        index_page.add_child(instance=project)

        # Create 2 favorable votes
        for i, choice in enumerate([VoteChoice.FAVORABLE, VoteChoice.RATHER_FAVORABLE]):
            user = User.objects.create_user(
                email=f"allfav{i}@example.com",
                password="TestPass123",
                first_name=f"User{i}",
                last_name="Tester",
            )
            FormResponse.objects.create(user=user, project=project, choice=choice)

        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project.pk}/")

        assert response.status_code == 200
        context = response.context

        assert context["favorable_total"] == 2
        assert context["unfavorable_total"] == 0
        assert context["favorable_percentage"] == 100.0
        assert context["unfavorable_percentage"] == 0

    def test_all_unfavorable_votes(self, client, admin_user, db):
        """Test percentages when all votes are unfavorable."""
        from wagtail.models import Page

        root_page = Page.objects.get(depth=1)

        index_page = PublicationIndexPage.objects.first()
        if not index_page:
            index_page = PublicationIndexPage(
                title="Publications",
                slug="publications-all-unfavorable",
            )
            root_page.add_child(instance=index_page)

        project = ProjectPage(
            title="All Unfavorable Project",
            slug="all-unfavorable-project",
            enable_voting=True,
        )
        index_page.add_child(instance=project)

        # Create 2 unfavorable votes
        for i, choice in enumerate([VoteChoice.UNFAVORABLE, VoteChoice.RATHER_UNFAVORABLE]):
            user = User.objects.create_user(
                email=f"allunfav{i}@example.com",
                password="TestPass123",
                first_name=f"User{i}",
                last_name="Tester",
            )
            FormResponse.objects.create(user=user, project=project, choice=choice)

        client.force_login(admin_user)
        response = client.get(f"/admin/vote-statistics/{project.pk}/")

        assert response.status_code == 200
        context = response.context

        assert context["favorable_total"] == 0
        assert context["unfavorable_total"] == 2
        assert context["favorable_percentage"] == 0
        assert context["unfavorable_percentage"] == 100.0

    def test_grouping_uses_correct_choices(self, client, admin_user, project_with_mixed_votes):
        """Test that grouping correctly classifies all VoteChoice values."""
        # Verify that the constants are correctly defined
        assert VoteChoice.FAVORABLE.value in FAVORABLE_VALUES
        assert VoteChoice.RATHER_FAVORABLE.value in FAVORABLE_VALUES
        assert VoteChoice.UNFAVORABLE.value in UNFAVORABLE_VALUES
        assert VoteChoice.RATHER_UNFAVORABLE.value in UNFAVORABLE_VALUES

        # Verify no overlap
        assert set(FAVORABLE_VALUES).isdisjoint(set(UNFAVORABLE_VALUES))

        # Verify all choices are covered
        all_choices = set(choice.value for choice in VoteChoice)
        grouped_choices = set(FAVORABLE_VALUES) | set(UNFAVORABLE_VALUES)
        assert all_choices == grouped_choices
