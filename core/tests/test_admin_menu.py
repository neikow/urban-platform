import pytest
from django.test import RequestFactory
from wagtail.admin.menu import admin_menu

from core.admin_menu import menu_entries
from core.models import User, UserRole


@pytest.fixture(autouse=True)
def fresh_menu():
    # Entries point at pages: rebuild them for the pages of each test database.
    menu_entries.cache_clear()
    yield
    menu_entries.cache_clear()


def menu_for(user):
    """{top-level name: [sub-entry names]} of the sidebar as ``user`` sees it."""
    request = RequestFactory().get("/admin/")
    request.user = user
    return {
        item.name: [sub.name for sub in item.menu.menu_items_for_request(request)]
        if hasattr(item, "menu")
        else []
        for item in sorted(admin_menu.menu_items_for_request(request), key=lambda i: i.order)
    }


def settings_urls(user):
    """URLs of the Paramètres entries: their names depend on the active language."""
    request = RequestFactory().get("/admin/")
    request.user = user
    settings = next(i for i in admin_menu.menu_items_for_request(request) if i.name == "settings")
    return [entry.url for entry in settings.menu.menu_items_for_request(request)]


ANNOUNCEMENT_URL = "/admin/settings/core/announcement/"
USERS_URL = "/admin/users/"
TASKS_URL = "/admin/tasks/"
MAP_URL = "/admin/settings/publications/mapsettings/"
FEATURES_URL = "/admin/settings/core/featureflags/"
ASSOCIATIONS_URL = "/admin/neighborhood_association/"
LEGAL_PAGES_IN_MENU = 4


def make_user(role, email, **kwargs):
    return User.objects.create_user(email=email, password="pass12345", role=role, **kwargs)


@pytest.mark.django_db
class TestAdminMenu:
    def test_grouped_by_task(self):
        superuser = User.objects.create_superuser(email="root@example.com", password="pass12345")

        menu = menu_for(superuser)

        assert list(menu)[:6] == [
            "home-page",
            "news",
            "useful-information",
            "site-pages",
            "participation",
            "media",
        ]
        assert "documentation" in menu and "settings" in menu
        for replaced in ("explorer", "images", "documents", "reports", "help"):
            assert replaced not in menu
        assert menu["participation"] == ["votes", "ideas"]
        assert menu["media"] == ["images", "documents"]
        assert len(menu["site-pages"]) == 7

    def test_administrators_manage_the_website(self):
        admin = make_user(UserRole.ADMIN, "admin@example.com")

        urls = settings_urls(admin)

        for url in (
            ANNOUNCEMENT_URL,
            TASKS_URL,
            USERS_URL,
            MAP_URL,
            FEATURES_URL,
            ASSOCIATIONS_URL,
        ):
            assert url in urls, url
        assert "participation" in menu_for(admin)
        assert len(menu_for(admin)["site-pages"]) == 7

    def test_moderators_get_the_announcement_and_statistics(self):
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")

        menu = menu_for(moderator)

        assert settings_urls(moderator) == [ANNOUNCEMENT_URL]
        assert menu["participation"] == ["votes", "ideas"]
        assert "news" in menu and "useful-information" in menu and "media" in menu

    def test_editors_get_content_only(self):
        editor = make_user(UserRole.EDITOR, "editor@example.com")

        menu = menu_for(editor)

        assert "news" in menu and "useful-information" in menu and "media" in menu
        assert "participation" not in menu
        assert "settings" not in menu
        # The legal pages are for administrators.
        assert len(menu["site-pages"]) == 7 - LEGAL_PAGES_IN_MENU

    def test_citizens_see_nothing(self):
        citizen = make_user(UserRole.CITIZEN, "citizen@example.com")

        assert menu_for(citizen) == {}

    def test_settings_managed_in_code_are_hidden(self):
        superuser = User.objects.create_superuser(email="root@example.com", password="pass12345")
        request = RequestFactory().get("/admin/")
        request.user = superuser
        settings = next(
            i for i in admin_menu.menu_items_for_request(request) if i.name == "settings"
        )

        names = {entry.name for entry in settings.menu.menu_items_for_request(request)}

        assert "users" in names
        assert not names & {"workflows", "workflow-tasks", "groups", "locales"}
