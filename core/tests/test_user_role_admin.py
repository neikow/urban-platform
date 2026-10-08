import importlib

import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.urls import reverse

from core.models import User, UserRole
from core.permissions import assignable_roles, can_assign_role, can_change_role
from core.roles import EDITORS_GROUP, MODERATORS_GROUP, is_last_administrator
from core.wagtail_forms import RoleUserCreationForm, RoleUserEditForm


# --- fixtures ---------------------------------------------------------------


def make_user(role: str, email: str, **fields: object) -> User:
    return User.objects.create_user(
        email=email, password="pass12345", first_name="First", last_name="Last", role=role, **fields
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="super@example.com", password="pass12345")


@pytest.fixture
def admin(db):
    return make_user(UserRole.ADMIN, "admin@example.com")


@pytest.fixture
def moderator(db):
    return make_user(UserRole.MODERATOR, "mod@example.com")


@pytest.fixture
def editor(db):
    return make_user(UserRole.EDITOR, "editor@example.com")


@pytest.fixture
def citizen(db):
    return make_user(UserRole.CITIZEN, "citizen@example.com")


def edit_post_data(instance: User, **overrides: object) -> dict:
    """Build a complete, valid POST payload for the user edit form."""
    data: dict[str, object] = {
        "email": instance.email,
        "first_name": instance.first_name or "First",
        "last_name": instance.last_name or "Last",
        "role": instance.role,
        "is_active": "on",
        "password1": "",
        "password2": "",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def group_names(user: User) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


# --- role ladder ------------------------------------------------------------


@pytest.mark.django_db
class TestRoleLadder:
    def test_each_role_includes_the_previous(self, editor, moderator, admin):
        assert editor.has_role(UserRole.EDITOR) and not editor.has_role(UserRole.MODERATOR)
        assert moderator.has_role(UserRole.EDITOR) and moderator.has_role(UserRole.MODERATOR)
        assert not moderator.has_role(UserRole.ADMIN)
        assert admin.has_role(UserRole.ADMIN)

    def test_superusers_have_every_role(self, superuser):
        assert superuser.has_role(UserRole.ADMIN)

    def test_citizens_have_no_staff_role(self, citizen):
        assert citizen.has_role(UserRole.CITIZEN)
        assert not citizen.has_role(UserRole.EDITOR)


# --- groups follow the role -------------------------------------------------


@pytest.mark.django_db
class TestRoleGroups:
    def test_each_role_gets_its_group(self, citizen, editor, moderator, admin):
        assert group_names(citizen) == set()
        assert group_names(editor) == {EDITORS_GROUP}
        assert group_names(moderator) == {MODERATORS_GROUP}
        assert group_names(admin) == {MODERATORS_GROUP}

    def test_changing_the_role_moves_the_user(self, editor):
        editor.role = UserRole.MODERATOR
        editor.save()
        assert group_names(editor) == {MODERATORS_GROUP}

        editor.role = UserRole.CITIZEN
        editor.save()
        assert group_names(editor) == set()

    def test_deactivated_accounts_leave_the_groups(self, moderator):
        moderator.is_active = False
        moderator.save()
        assert group_names(moderator) == set()

    def test_other_groups_are_left_alone(self, editor):
        other = Group.objects.create(name="Newsletter team")
        editor.groups.add(other)
        editor.role = UserRole.MODERATOR
        editor.save()
        assert group_names(editor) == {MODERATORS_GROUP, "Newsletter team"}

    def test_login_does_not_touch_groups(self, editor, django_assert_max_num_queries):
        with django_assert_max_num_queries(1):
            editor.save(update_fields=["last_login"])

    def test_admin_form_keeps_groups_in_step(self, admin, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, role=UserRole.EDITOR), instance=citizen, for_user=admin
        )
        assert form.is_valid(), form.errors
        form.save()
        assert group_names(citizen) == {EDITORS_GROUP}
        assert form.fields["groups"].disabled


# --- who assigns roles ------------------------------------------------------


@pytest.mark.django_db
class TestAssignableRoles:
    def test_administrators_assign_every_role(self, superuser, admin):
        everything = [UserRole.CITIZEN, UserRole.EDITOR, UserRole.MODERATOR, UserRole.ADMIN]
        assert assignable_roles(superuser) == everything
        assert assignable_roles(admin) == everything

    @pytest.mark.parametrize("role", [UserRole.CITIZEN, UserRole.EDITOR, UserRole.MODERATOR])
    def test_others_assign_nothing(self, role):
        assert assignable_roles(make_user(role, f"{role}@example.com")) == []

    def test_anonymous_assigns_nothing(self):
        assert assignable_roles(None) == []

    def test_can_assign_and_change(self, admin, moderator):
        assert can_assign_role(admin, UserRole.ADMIN)
        assert not can_assign_role(moderator, UserRole.EDITOR)
        assert can_change_role(moderator, UserRole.ADMIN, UserRole.ADMIN)
        assert not can_change_role(moderator, UserRole.CITIZEN, UserRole.EDITOR)
        assert can_change_role(admin, UserRole.CITIZEN, UserRole.ADMIN)


@pytest.mark.django_db
class TestRoleUserForms:
    def test_admin_sees_every_role(self, admin, citizen):
        form = RoleUserEditForm(instance=citizen, for_user=admin)
        assert [v for v, _ in form.fields["role"].choices] == list(UserRole.values)

    def test_role_locked_for_others(self, moderator, editor):
        form = RoleUserEditForm(instance=editor, for_user=moderator)
        assert [v for v, _ in form.fields["role"].choices] == [UserRole.EDITOR]

    def test_admin_promotes(self, admin, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, role=UserRole.MODERATOR), instance=citizen, for_user=admin
        )
        assert form.is_valid(), form.errors
        form.save()
        citizen.refresh_from_db()
        assert citizen.role == UserRole.MODERATOR

    def test_admin_creates_an_editor(self, admin):
        form = RoleUserCreationForm(
            data={
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
                "role": UserRole.EDITOR,
                "password1": "SomePass12345",
                "password2": "SomePass12345",
            },
            for_user=admin,
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.role == UserRole.EDITOR
        assert group_names(user) == {EDITORS_GROUP}

    def test_subscription_date_follows_the_checkbox(self, admin, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, is_subscriber="on"), instance=citizen, for_user=admin
        )
        assert form.is_valid(), form.errors
        form.save()
        citizen.refresh_from_db()
        assert citizen.is_subscriber and citizen.subscribed_at is not None

        form = RoleUserEditForm(data=edit_post_data(citizen), instance=citizen, for_user=admin)
        assert form.is_valid(), form.errors
        form.save()
        citizen.refresh_from_db()
        assert not citizen.is_subscriber and citizen.subscribed_at is None


# --- the last administrator -------------------------------------------------


@pytest.mark.django_db
class TestLastAdministrator:
    def test_detection(self, admin):
        assert is_last_administrator(admin)
        make_user(UserRole.ADMIN, "other-admin@example.com")
        assert not is_last_administrator(admin)

    def test_superusers_count(self, admin, superuser):
        assert not is_last_administrator(admin)

    def test_cannot_be_demoted(self, admin):
        form = RoleUserEditForm(
            data=edit_post_data(admin, role=UserRole.MODERATOR), instance=admin, for_user=admin
        )
        assert not form.is_valid()
        assert form.has_error("__all__", code="last_administrator")

    def test_cannot_be_deactivated(self, admin):
        form = RoleUserEditForm(
            data=edit_post_data(admin, is_active=None), instance=admin, for_user=admin
        )
        assert not form.is_valid()

    def test_can_be_demoted_once_another_exists(self, admin):
        make_user(UserRole.ADMIN, "other-admin@example.com")
        form = RoleUserEditForm(
            data=edit_post_data(admin, role=UserRole.MODERATOR), instance=admin, for_user=admin
        )
        assert form.is_valid(), form.errors

    def test_deletion_hook_refuses(self, rf, admin):
        from django.contrib.messages.storage.fallback import FallbackStorage

        from core.wagtail_hooks import keep_one_administrator

        request = rf.post("/")
        request.session = {}
        request._messages = FallbackStorage(request)

        response = keep_one_administrator(request, admin)

        assert response is not None and response.status_code == 302
        make_user(UserRole.ADMIN, "other-admin@example.com")
        assert keep_one_administrator(request, admin) is None

    def test_cannot_delete_own_account(self, client, admin):
        admin.is_verified = True
        admin.save()
        client.force_login(admin)

        response = client.post(
            reverse("account_delete"), {"password": "pass12345", "confirm": "on"}
        )

        assert response.status_code == 200
        admin.refresh_from_db()
        assert admin.is_active


# --- role-derived permissions ----------------------------------------------


@pytest.mark.django_db
class TestRoleDerivedPermissions:
    """The ``RolePermissionsBackend`` grants admin perms from the role alone."""

    EDITOR_PERMS = {"wagtailadmin.access_admin"}
    MODERATOR_PERMS = EDITOR_PERMS | {"core.change_announcement", "core.view_participation_stats"}
    ADMIN_PERMS = MODERATOR_PERMS | {
        "core.change_user",
        "core.change_neighborhoodassociation",
        "core.change_featureflags",
        "core.manage_tasks",
        "publications.change_mapsettings",
    }
    EVERYTHING = ADMIN_PERMS

    def granted(self, user: User) -> set[str]:
        return {perm for perm in self.EVERYTHING if user.has_perm(perm)}

    def test_matrix(self, citizen, editor, moderator, admin):
        assert self.granted(citizen) == set()
        assert self.granted(editor) == self.EDITOR_PERMS
        assert self.granted(moderator) == self.MODERATOR_PERMS
        assert self.granted(admin) == self.ADMIN_PERMS

    def test_inactive_admin_gets_no_role_perms(self, admin):
        User.objects.create_user(email="spare@example.com", password="x", role=UserRole.ADMIN)
        admin.is_active = False
        admin.save()
        assert not admin.has_perm("core.change_user")

    def test_admin_reaches_users_index(self, client, admin):
        client.force_login(admin)
        assert client.get(reverse("wagtailusers_users:index")).status_code == 200

    def test_moderator_cannot_reach_users_index(self, client, moderator):
        client.force_login(moderator)
        assert client.get(reverse("wagtailusers_users:index")).status_code in (302, 403)

    def test_admin_reaches_the_site_settings(self, client, admin):
        client.force_login(admin)
        for url in (
            reverse("neighborhood_association:index"),
            reverse("wagtailsettings:edit", args=["publications", "mapsettings"]),
            reverse("wagtailsettings:edit", args=["core", "featureflags"]),
            reverse("admin_tasks"),
        ):
            assert client.get(url, follow=True).status_code == 200, url

    def test_moderator_does_not(self, client, moderator):
        client.force_login(moderator)
        for url in (
            reverse("neighborhood_association:index"),
            reverse("wagtailsettings:edit", args=["core", "featureflags"]),
            reverse("admin_tasks"),
        ):
            assert client.get(url).status_code in (302, 403), url


# --- migration of the former roles ------------------------------------------


@pytest.mark.django_db
def test_association_members_become_editors_or_moderators():
    migration = importlib.import_module("core.migrations.0017_roles_and_features")
    publisher = make_user(UserRole.CITIZEN, "publisher@example.com")
    writer = make_user(UserRole.CITIZEN, "writer@example.com")
    User.objects.filter(pk__in=[publisher.pk, writer.pk]).update(role="ASSOCIATION_MEMBER")
    publisher.groups.add(Group.objects.get(name=MODERATORS_GROUP))

    migration.map_roles(apps, None)

    publisher.refresh_from_db()
    writer.refresh_from_db()
    assert publisher.role == UserRole.MODERATOR
    assert writer.role == UserRole.EDITOR
    assert group_names(writer) == {EDITORS_GROUP}


@pytest.mark.django_db
def test_edit_page_shows_role_subscription_and_locked_groups(client, admin, editor):
    client.force_login(admin)

    content = client.get(reverse("wagtailusers_users:edit", args=[editor.pk])).content.decode()

    assert 'name="role"' in content
    assert 'name="is_subscriber"' in content
    groups = content[content.index('name="groups"') - 300 : content.index('name="groups"') + 300]
    assert "disabled" in groups


@pytest.mark.django_db
def test_admin_saves_through_the_page(client, admin, citizen):
    client.force_login(admin)

    response = client.post(
        reverse("wagtailusers_users:edit", args=[citizen.pk]),
        data=edit_post_data(citizen, role=UserRole.MODERATOR, is_subscriber="on"),
    )

    assert response.status_code == 302
    citizen.refresh_from_db()
    assert citizen.role == UserRole.MODERATOR and citizen.is_subscriber
    assert group_names(citizen) == {MODERATORS_GROUP}
