import pytest

from home.models import HomePage
from publications.models import ParticipationMode, ProjectPage, PublicationIndexPage


@pytest.mark.django_db
def test_login_dialog_rendered_once_on_project_pages(client):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
    project = ProjectPage(title="P", slug="p", participation_mode=ParticipationMode.VOTING)
    index.add_child(instance=project)
    project.save_revision().publish()

    content = client.get(project.url).content.decode()

    assert content.count('id="login_modal"') == 1
