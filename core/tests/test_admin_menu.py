import pytest
from django.contrib.auth.models import Group
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

    def test_administrators_manage_users_and_the_announcement(self):
        admin = make_user(UserRole.ADMIN, "admin@example.com")

        settings = menu_for(admin)["settings"]

        assert "users" in settings
        assert "annonce" in settings

    def test_association_members_do_not_see_user_management(self):
        member = make_user(UserRole.ASSOCIATION_MEMBER, "member@example.com")

        menu = menu_for(member)

        assert menu["settings"] == ["annonce"]
        # No page permissions without a group: no content entries.
        assert "news" not in menu and "site-pages" not in menu

    def test_content_entries_follow_page_permissions(self):
        member = make_user(UserRole.ASSOCIATION_MEMBER, "editor@example.com")
        member.groups.add(Group.objects.get(name="Moderators"))

        menu = menu_for(member)

        assert "news" in menu and "useful-information" in menu and "site-pages" in menu
        assert "users" not in menu["settings"]

    def test_citizens_see_nothing(self):
        citizen = make_user(UserRole.CITIZEN, "citizen@example.com")

        assert menu_for(citizen) == {}
