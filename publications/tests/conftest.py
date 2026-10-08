import pytest
from wagtail.models import Page

from publications.models import ParticipationMode, ProjectPage, PublicationIndexPage


@pytest.fixture
def publication_index(db):
    index_page = PublicationIndexPage.objects.first()
    if not index_page:
        index_page = PublicationIndexPage(title="Publications", slug="publications")
        Page.objects.get(depth=1).add_child(instance=index_page)
    return index_page


@pytest.fixture
def voting_project(publication_index):
    project = ProjectPage(
        title="Voting", slug="voting", participation_mode=ParticipationMode.VOTING
    )
    publication_index.add_child(instance=project)
    return project


@pytest.fixture
def ideas_project(publication_index):
    project = ProjectPage(title="Ideas", slug="ideas", participation_mode=ParticipationMode.IDEAS)
    publication_index.add_child(instance=project)
    return project
