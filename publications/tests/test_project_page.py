import pytest

from publications.models import ParticipationMode, ProjectPage, PublicationIndexPage


@pytest.fixture
def publication_index(db):
    from wagtail.models import Page

    root = Page.objects.get(depth=1)
    index = PublicationIndexPage.objects.first()
    if not index:
        index = PublicationIndexPage(title="Publications", slug="publications")
        root.add_child(instance=index)
    return index


def _published_project(index, slug, mode):
    project = ProjectPage(title=slug, slug=slug, participation_mode=mode)
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


@pytest.mark.django_db
class TestProjectPageParticipationRendering:
    """The public project page renders the participation block matching the mode."""

    def test_voting_mode_renders_vote_component(self, client, publication_index):
        project = _published_project(publication_index, "p-vote", ParticipationMode.VOTING)
        body = client.get(project.url).content.decode()
        assert "vote-component" in body
        assert "ideas-component" not in body

    def test_ideas_mode_renders_ideas_component(self, client, publication_index):
        project = _published_project(publication_index, "p-idea", ParticipationMode.IDEAS)
        body = client.get(project.url).content.decode()
        assert "ideas-component" in body
        assert "vote-component" not in body

    def test_none_mode_renders_neither(self, client, publication_index):
        project = _published_project(publication_index, "p-none", ParticipationMode.NONE)
        body = client.get(project.url).content.decode()
        assert "vote-component" not in body
        assert "ideas-component" not in body
