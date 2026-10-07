import json

import pytest
from django.urls import reverse
from django.utils.html import escape

from about.models import AboutCommissionPage, AboutDevTeamPage, AboutWebsitePage
from core.models import User
from core.page_templates import get_template, pending_template, rich_text, templates_for
from core.wagtail_hooks import choose_page_template
from home.models import HomePage
from legal.models import LegalIndexPage
from pedagogy.models import PedagogyCardPage, PedagogyIndexPage
from publications.models import (
    EventPage,
    ParticipationMode,
    ProjectPage,
    PublicationIndexPage,
)

PAGE_TYPES = [
    HomePage,
    AboutWebsitePage,
    AboutCommissionPage,
    AboutDevTeamPage,
    ProjectPage,
    EventPage,
    PublicationIndexPage,
    PedagogyCardPage,
    PedagogyIndexPage,
]
ALL_TEMPLATES = [
    (page_class, template) for page_class in PAGE_TYPES for template in templates_for(page_class)
]


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="admin@example.com", password="pass12345")


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


def add_url(page_class, parent, **query):
    url = reverse(
        "wagtailadmin_pages:add",
        args=[page_class._meta.app_label, page_class._meta.model_name, parent.pk],
    )
    return url + ("?" + "&".join(f"{k}={v}" for k, v in query.items()) if query else "")


@pytest.mark.django_db
class TestTemplates:
    def test_every_page_type_offers_templates(self):
        for page_class in PAGE_TYPES:
            assert templates_for(page_class), page_class

    @pytest.mark.parametrize(
        ("page_class", "template"),
        ALL_TEMPLATES,
        ids=[f"{c.__name__}-{t.slug}" for c, t in ALL_TEMPLATES],
    )
    def test_content_is_valid_for_its_page_type(self, page_class, template):
        field = page_class._meta.get_field("content")

        stream = field.to_python(json.dumps(template.content()))
        field.stream_block.clean(stream)

    def test_outline_shows_section_headings(self):
        template = get_template(ProjectPage, "vote")

        outline = template.outline(ProjectPage)

        assert outline[0] == "Le projet en bref"
        assert "Questions" in outline[-1] or "FAQ" in outline[-1]  # the FAQ block's label

    def test_rich_text_helper(self):
        assert rich_text("<p>Bonjour</p>")["value"]["text"] == "<p>Bonjour</p>"


@pytest.mark.django_db
class TestCreatingAPage:
    def test_a_chooser_comes_before_the_editor(self, client, admin, index):
        client.force_login(admin)

        content = client.get(add_url(ProjectPage, index)).content.decode()

        for template in templates_for(ProjectPage):
            assert escape(str(template.name)) in content
            assert "template=" + template.slug in content
        assert "blank=1" in content

    def test_the_template_fills_the_editor(self, client, admin, index):
        client.force_login(admin)

        response = client.get(add_url(ProjectPage, index, template="ideas"))

        form = response.context["form"]
        assert "Sur quoi vos idées sont attendues" in form.instance.content[1].value["text"].source
        assert form.instance.participation_mode == ParticipationMode.IDEAS
        assert pending_template.get() is None

    def test_a_blank_page(self, client, admin, index):
        client.force_login(admin)

        content = client.get(add_url(EventPage, index, blank=1)).content.decode()

        assert "Ordre du jour" not in content
        assert 'name="title"' in content

    def test_unknown_template(self, client, admin, index):
        client.force_login(admin)

        assert client.get(add_url(ProjectPage, index, template="nope")).status_code == 404

    def test_page_types_without_templates_go_straight_to_the_editor(self, rf, admin, index):
        request = rf.get("/")
        request.user = admin

        assert choose_page_template(request, index.get_parent(), LegalIndexPage) is None

    def test_saving_is_not_intercepted(self, rf, admin, index):
        request = rf.post("/")
        request.user = admin

        assert choose_page_template(request, index, EventPage) is None


@pytest.mark.django_db
class TestApplyingToAnExistingPage:
    def test_replaces_the_content_in_a_draft(self, client, admin, index):
        project = ProjectPage(
            title="Jardin", slug="jardin", participation_mode=ParticipationMode.NONE
        )
        index.add_child(instance=project)
        project.save_revision().publish()
        client.force_login(admin)

        response = client.post(reverse("page_templates", args=[project.pk]), {"template": "vote"})

        assert response.status_code == 302
        project.refresh_from_db()
        assert list(project.content) == []  # live page unchanged
        draft = project.get_latest_revision_as_object()
        assert "Le projet en bref" in draft.content[0].value["text"].source
        # Only the content changes on an existing page.
        assert draft.participation_mode == ParticipationMode.NONE

    def test_not_offered_for_pages_without_templates(self, client, admin):
        client.force_login(admin)
        legal_index = LegalIndexPage.objects.get()

        assert client.get(reverse("page_templates", args=[legal_index.pk])).status_code == 404

    def test_index_page_template_keeps_its_list(self, client, admin, index):
        client.force_login(admin)

        response = client.post(reverse("page_templates", args=[index.pk]), {"template": "complete"})

        assert response.status_code == 302
        draft = index.get_latest_revision_as_object()
        assert [block.block_type for block in draft.content].count("publication_list") == 1
