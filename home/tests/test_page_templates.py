import json

import pytest
from django.urls import reverse
from django.utils.html import escape

from core.models import User, UserRole
from home.models import HomePage
from core.page_templates import get_template
from home.page_templates import TEMPLATES

HERO = {
    "type": "hero",
    "value": {
        "title": "Urba7Marseille",
        "subtitle": "",
        "image": None,
        "alt_text": "Le Vieux-Port",
        "cta_link": "",
        "cta_text": "",
    },
}


@pytest.fixture
def home(db):
    return HomePage.objects.get(slug="home")


@pytest.fixture
def editor(db):
    return User.objects.create_user(
        email="editor@example.com", password="pass12345", role=UserRole.ADMIN, is_superuser=True
    )


@pytest.mark.django_db
class TestTemplates:
    @pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.slug)
    def test_content_is_valid_home_page_content(self, home, template):
        field = HomePage._meta.get_field("content")

        stream = field.to_python(json.dumps(template.content([])))
        field.stream_block.clean(stream)

    @pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.slug)
    def test_home_page_renders_with_it(self, client, home, template):
        home.content = json.dumps(template.content([]))
        home.save_revision().publish()

        response = client.get(home.url)

        assert response.status_code == 200
        # Live parts are hidden when there is nothing to show; written parts always show.
        content = response.content.decode()
        for block in template.blocks:
            if block["type"] in ("section", "join"):
                assert escape(block["value"]["title"]) in content

    def test_keeps_the_current_hero(self):
        content = get_template(HomePage, "essentials").content([HERO, {"type": "faq", "value": []}])

        assert content[0] == HERO
        assert [block["type"] for block in content[1:]] == [
            block["type"] for block in get_template(HomePage, "essentials").blocks
        ]


@pytest.mark.django_db
class TestTemplatesAdmin:
    def url(self, home):
        return reverse("page_templates", args=[home.pk])

    def test_lists_the_templates(self, client, home, editor):
        client.force_login(editor)

        content = client.get(self.url(home)).content.decode()

        for template in TEMPLATES:
            assert escape(str(template.name)) in content

    def test_applying_saves_a_draft_and_leaves_the_live_page(self, client, home, editor):
        home.content = json.dumps([HERO])
        home.save_revision().publish()
        client.force_login(editor)

        response = client.post(self.url(home), {"template": "essentials"})

        assert response.status_code == 302
        assert response["Location"] == reverse("wagtailadmin_pages:edit", args=[home.pk])
        home.refresh_from_db()
        assert home.has_unpublished_changes
        assert [block.block_type for block in home.content] == ["hero"]  # live: unchanged
        draft = home.get_latest_revision_as_object()
        assert [block.block_type for block in draft.content][:2] == ["hero", "open_projects"]
        assert home.get_latest_revision().user == editor

    def test_unknown_template(self, client, home, editor):
        client.force_login(editor)

        assert client.post(self.url(home), {"template": "nope"}).status_code == 404

    def test_needs_permission_to_edit_the_home_page(self, client, home):
        member = User.objects.create_user(
            email="member@example.com", password="pass12345", role=UserRole.CITIZEN
        )
        client.force_login(member)

        assert client.get(self.url(home)).status_code in (302, 403)
        assert client.post(self.url(home), {"template": "essentials"}).status_code in (302, 403)
        home.refresh_from_db()
        assert not home.has_unpublished_changes
