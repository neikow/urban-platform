import pytest

from core.models import User
from publications.models import (
    IdeaResponse,
    ParticipationMode,
    ProjectPage,
    PublicationIndexPage,
)


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email="local@example.com",
        password="UserPass123",
        first_name="Local",
        last_name="User",
        postal_code="13007",
    )


def _index(db):
    from wagtail.models import Page

    root_page = Page.objects.get(depth=1)
    index_page = PublicationIndexPage.objects.first()
    if not index_page:
        index_page = PublicationIndexPage(title="Publications", slug="publications")
        root_page.add_child(instance=index_page)
    return index_page


@pytest.fixture
def project_with_ideas(db, regular_user):
    index_page = _index(db)
    project = ProjectPage(
        title="Ideas Project",
        slug="ideas-project",
        participation_mode=ParticipationMode.IDEAS,
    )
    index_page.add_child(instance=project)
    IdeaResponse.objects.create(
        user=regular_user, project=project, description="Plant trees on the boulevard"
    )
    return project


@pytest.mark.django_db
class TestIdeaStatsView:
    def test_requires_admin_authentication(self, client):
        response = client.get("/admin/idea-collection/")
        assert response.status_code == 302
        assert "/admin/login/" in response.url

    def test_accessible_by_admin(self, client, admin_user, project_with_ideas):
        client.force_login(admin_user)
        response = client.get("/admin/idea-collection/")
        assert response.status_code == 200

    def test_lists_projects_collecting_ideas(self, client, admin_user, project_with_ideas):
        client.force_login(admin_user)
        response = client.get("/admin/idea-collection/")
        assert response.status_code == 200
        assert b"Ideas Project" in response.content

    def test_excludes_voting_projects(self, client, admin_user, project_with_ideas):
        index_page = _index(None)
        voting = ProjectPage(
            title="A Voting Only Project",
            slug="voting-only",
            participation_mode=ParticipationMode.VOTING,
        )
        index_page.add_child(instance=voting)

        client.force_login(admin_user)
        response = client.get("/admin/idea-collection/")
        pks = {s["project"].pk for s in response.context["projects_stats"]}
        assert project_with_ideas.pk in pks
        assert voting.pk not in pks


@pytest.mark.django_db
class TestIdeaStatsDetailView:
    def test_accessible_by_admin(self, client, admin_user, project_with_ideas):
        client.force_login(admin_user)
        response = client.get(f"/admin/idea-collection/{project_with_ideas.pk}/")
        assert response.status_code == 200

    def test_displays_idea_text(self, client, admin_user, project_with_ideas):
        client.force_login(admin_user)
        response = client.get(f"/admin/idea-collection/{project_with_ideas.pk}/")
        assert b"Plant trees on the boulevard" in response.content

    def test_returns_404_for_nonexistent_project(self, client, admin_user, db):
        client.force_login(admin_user)
        response = client.get("/admin/idea-collection/99999/")
        assert response.status_code == 404

    def test_anonymous_idea_hides_email(self, client, admin_user, db):
        index_page = _index(db)
        project = ProjectPage(
            title="Anon Ideas",
            slug="anon-ideas",
            participation_mode=ParticipationMode.IDEAS,
        )
        index_page.add_child(instance=project)
        anon = User.objects.create_user(
            email="anon_idea@example.com",
            password="TestPass123",
            first_name="Anon",
            last_name="User",
            postal_code="13007",
        )
        IdeaResponse.objects.create(
            user=anon, project=project, description="A secret idea", anonymize=True
        )

        client.force_login(admin_user)
        response = client.get(f"/admin/idea-collection/{project.pk}/")
        content = response.content.decode()
        assert "A secret idea" in content
        assert "anon_idea@example.com" not in content
        assert "Anonymous" in content or "Anonyme" in content


@pytest.mark.django_db
class TestIdeaStatsLocalFilter:
    @pytest.fixture
    def project_local_and_outside(self, db):
        index_page = _index(db)
        project = ProjectPage(
            title="Local Filter Ideas",
            slug="local-filter-ideas",
            participation_mode=ParticipationMode.IDEAS,
        )
        index_page.add_child(instance=project)

        local = User.objects.create_user(
            email="local_idea@example.com",
            password="TestPass123",
            first_name="Local",
            last_name="Voter",
            postal_code="13007",
        )
        IdeaResponse.objects.create(user=local, project=project, description="Local idea")

        outside = User.objects.create_user(
            email="outside_idea@example.com",
            password="TestPass123",
            first_name="Outside",
            last_name="Voter",
            postal_code="75001",
        )
        IdeaResponse.objects.create(user=outside, project=project, description="Outside idea")
        return project

    def test_detail_hides_outside_by_default(self, client, admin_user, project_local_and_outside):
        client.force_login(admin_user)
        response = client.get(f"/admin/idea-collection/{project_local_and_outside.pk}/")
        assert response.context["total_ideas"] == 1
        content = response.content.decode()
        assert "Local idea" in content
        assert "Outside idea" not in content

    def test_detail_shows_all_with_show_all(self, client, admin_user, project_local_and_outside):
        client.force_login(admin_user)
        response = client.get(f"/admin/idea-collection/{project_local_and_outside.pk}/?show_all=1")
        assert response.context["total_ideas"] == 2
        content = response.content.decode()
        assert "Local idea" in content
        assert "Outside idea" in content
