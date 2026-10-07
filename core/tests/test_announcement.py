import pytest
from django.urls import reverse

from core.models import Announcement, AnnouncementStyle, User, UserRole
from core.templatetags.announcement_tags import DISMISSED_COOKIE
from home.models import HomePage

MESSAGE = '<p>Travaux <b>rue de la Corniche</b> : <a href="https://example.com">détails</a></p>'


@pytest.fixture
def home_url(db):
    return HomePage.objects.get(slug="home").url


@pytest.fixture
def announcement(db):
    announcement = Announcement.load()
    announcement.enabled = True
    announcement.message = MESSAGE
    announcement.save()
    return announcement


def band(client, url):
    content = client.get(url).content.decode()
    return 'aria-label="Announcement"' in content or 'aria-label="Annonce"' in content, content


@pytest.mark.django_db
class TestAnnouncementBand:
    def test_shows_the_rich_text_message(self, client, home_url, announcement):
        shown, content = band(client, home_url)

        assert shown
        assert "<b>rue de la Corniche</b>" in content
        assert 'href="https://example.com"' in content
        assert f'data-dismiss-cookie="{DISMISSED_COOKIE}={announcement.version}"' in content

    def test_hidden_when_disabled(self, client, home_url, announcement):
        announcement.enabled = False
        announcement.save()

        assert not band(client, home_url)[0]

    @pytest.mark.parametrize("message", ["", '<p data-block-key="x1"></p>'])
    def test_hidden_when_the_message_is_empty(self, client, home_url, announcement, message):
        announcement.message = message
        announcement.save()

        assert not band(client, home_url)[0]

    def test_hidden_once_dismissed(self, client, home_url, announcement):
        client.cookies[DISMISSED_COOKIE] = announcement.version

        assert not band(client, home_url)[0]

    def test_shown_again_when_the_message_changes(self, client, home_url, announcement):
        client.cookies[DISMISSED_COOKIE] = announcement.version
        announcement.message = "<p>Nouvelle réunion publique jeudi.</p>"
        announcement.save()

        assert band(client, home_url)[0]

    def test_version_follows_message_and_style(self, announcement):
        version = announcement.version
        announcement.style = AnnouncementStyle.IMPORTANT

        assert announcement.version != version


@pytest.mark.django_db
class TestAnnouncementAdmin:
    @pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.ASSOCIATION_MEMBER])
    def test_admin_roles_can_edit_it(self, client, role):
        user = User.objects.create_user(email="editor@example.com", password="pass12345", role=role)
        client.force_login(user)

        url = reverse("wagtailsettings:edit", args=["core", "announcement", Announcement.load().pk])
        response = client.post(
            url, {"enabled": "on", "message": '{"blocks": [], "entityMap": {}}', "style": "warning"}
        )

        assert user.has_perm("core.change_announcement")
        assert response.status_code == 302
        assert Announcement.load().style == "warning"

    def test_citizens_cannot(self, db):
        citizen = User.objects.create_user(
            email="c@example.com", password="pass12345", role=UserRole.CITIZEN
        )

        assert not citizen.has_perm("core.change_announcement")
