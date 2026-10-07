import pytest

from publications.models import ProjectPage, PublicationIndexPage


@pytest.fixture
def publication_index(db):
    from wagtail.models import Page

    root = Page.objects.get(depth=1)
    index = PublicationIndexPage.objects.first()
    if not index:
        index = PublicationIndexPage(title="Publications", slug="publications")
        root.add_child(instance=index)
    return index


def _published_project(index, title):
    project = ProjectPage(title=title, slug=title.lower())
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


@pytest.mark.django_db
class TestResultsRoute:
    """The "results" route renders the list region alone, for lib/instant-results.ts."""

    def test_renders_only_the_list_region(self, client, publication_index):
        _published_project(publication_index, "Jardin")

        response = client.get(publication_index.url + "results/")
        body = response.content.decode()

        assert response.status_code == 200
        assert body.lstrip().startswith("<div data-instant-results")
        assert "Jardin" in body
        assert "<html" not in body
        assert "projects-map" not in body
        assert response["X-Robots-Tag"] == "noindex"

    def test_applies_the_filters_of_the_query_string(self, client, publication_index):
        _published_project(publication_index, "Jardin")
        _published_project(publication_index, "Fontaine")

        body = client.get(publication_index.url + "results/?search=Fontaine").content.decode()

        assert "Fontaine" in body
        assert "Jardin" not in body
        assert 'data-summary="1 r' in body  # "1 result", or "1 résultat" once translated

    def test_page_points_the_region_at_the_route(self, client, publication_index):
        body = client.get(publication_index.url).content.decode()

        assert f'data-instant-url="{publication_index.url}results/"' in body
