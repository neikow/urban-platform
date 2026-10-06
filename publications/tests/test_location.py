import pytest

from core.models import User
from home.models import HomePage
from publications.geo import feature_collection
from publications.models import ProjectPage, PublicationIndexPage

POINT = {"type": "Point", "coordinates": [5.3601, 43.2841]}
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[5.35, 43.28], [5.36, 43.28], [5.36, 43.29], [5.35, 43.28]]],
}


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


def add_project(index, slug, location=None, live=True):
    project = ProjectPage(title=slug.title(), slug=slug, location=location, description="Desc")
    index.add_child(instance=project)
    if live:
        project.save_revision().publish()
    else:
        project.unpublish()
    return project


@pytest.mark.django_db
class TestProjectsMap:
    def test_only_located_live_projects_are_mapped(self, index):
        add_project(index, "point", POINT)
        add_project(index, "area", POLYGON)
        add_project(index, "nowhere")
        add_project(index, "draft", POINT, live=False)

        data = index.get_projects_map()

        assert data["type"] == "FeatureCollection"
        assert sorted(f["properties"]["title"] for f in data["features"]) == ["Area", "Point"]
        feature = next(f for f in data["features"] if f["properties"]["title"] == "Point")
        assert feature["geometry"] == POINT
        assert feature["properties"]["url"].endswith("/point/")

    def test_index_page_embeds_map_data(self, client, index):
        add_project(index, "point", POINT)

        content = client.get(index.url).content.decode()

        assert 'id="projects-map"' in content
        assert 'id="projects-map-data"' in content
        assert "dist/projects-map.js" in content
        assert "dist/map.css" in content

    def test_project_page_shows_its_location(self, client, index):
        project = add_project(index, "point", POINT)

        response = client.get(project.url)

        assert response.context["project_map"]["feature"]["geometry"] == POINT
        assert 'id="project-location-map"' in response.content.decode()

    def test_project_without_location_has_no_map(self, client, index):
        project = add_project(index, "nowhere")

        response = client.get(project.url)

        assert "project_map" not in response.context
        assert "dist/map.css" not in response.content.decode()

    def test_feature_collection_skips_missing_locations(self, index):
        projects = [add_project(index, "point", POINT), add_project(index, "nowhere")]

        assert len(feature_collection(projects)["features"]) == 1


@pytest.mark.django_db
def test_admin_saves_location_from_the_widget(client, index):
    admin = User.objects.create_superuser(
        email="admin@example.com", password="x", first_name="A", last_name="B"
    )
    project = add_project(index, "point")
    client.force_login(admin)

    edit_url = f"/admin/pages/{project.pk}/edit/"
    page = client.get(edit_url)
    assert "<geojson-map-input" in page.content.decode()

    project.location = POLYGON
    project.full_clean()
    project.save_revision().publish()
    project.refresh_from_db()
    assert project.location == POLYGON
