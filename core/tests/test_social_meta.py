import re

import pytest
from django.conf import settings

from home.models import HomePage
from publications.models import ProjectPage, PublicationIndexPage


def meta(content: str, attr: str, name: str) -> str | None:
    match = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', content)
    return match.group(1) if match else None


@pytest.fixture
def project(db):
    home = HomePage.objects.get(slug="home")
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        home.add_child(instance=index)
    project = ProjectPage(
        title="Jardin partagé", slug="jardin", description="Un jardin rue d'Endoume"
    )
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


@pytest.mark.django_db
class TestSocialMeta:
    def test_project_page_preview(self, client, project):
        content = client.get(project.url + "?utm_source=x").content.decode()

        assert meta(content, "property", "og:title") == "Jardin partagé"
        assert meta(content, "property", "og:type") == "article"
        assert meta(content, "property", "og:site_name") == settings.WEBSITE_NAME
        assert meta(content, "name", "description") == "Un jardin rue d&#x27;Endoume"
        assert meta(content, "name", "twitter:card") == "summary"
        # Canonical URL drops the query string.
        assert f'<link rel="canonical" href="http://testserver{project.url}">' in content
        assert meta(content, "property", "og:url") == f"http://testserver{project.url}"

    def test_search_description_wins_over_description(self, client, project):
        project.search_description = "Résumé SEO"
        project.save_revision().publish()

        content = client.get(project.url).content.decode()

        assert meta(content, "name", "description") == "Résumé SEO"

    def test_non_wagtail_page_has_site_preview(self, client, db):
        content = client.get("/auth/register/").content.decode()

        assert meta(content, "property", "og:title") == settings.WEBSITE_NAME
        assert '<link rel="canonical" href="http://testserver/auth/register/">' in content
