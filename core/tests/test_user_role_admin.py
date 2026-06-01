import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from core.models import User, UserRole
from core.permissions import assignable_roles, can_assign_role, can_change_role
from core.wagtail_forms import RoleUserCreationForm, RoleUserEditForm


# --- fixtures ---------------------------------------------------------------


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="super@example.com", password="pass12345")


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        first_name="Ada",
        last_name="Min",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def moderator(db):
    """An ASSOCIATION_MEMBER — the 'moderator' in the requirements."""
    return User.objects.create_user(
        email="mod@example.com",
        password="pass12345",
        first_name="Mod",
        last_name="Erator",
        role=UserRole.ASSOCIATION_MEMBER,
    )


@pytest.fixture
def citizen(db):
    return User.objects.create_user(
        email="citizen@example.com",
        password="pass12345",
        first_name="Cit",
        last_name="Izen",
        role=UserRole.CITIZEN,
    )


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
    return data


# --- permission helpers -----------------------------------------------------


@pytest.mark.django_db
class TestAssignableRoles:
    def test_superuser_can_assign_all_roles(self, superuser):
        assert assignable_roles(superuser) == [
            UserRole.CITIZEN,
            UserRole.ASSOCIATION_MEMBER,
            UserRole.ADMIN,
        ]

    def test_admin_can_assign_all_roles(self, admin):
        assert assignable_roles(admin) == [
            UserRole.CITIZEN,
            UserRole.ASSOCIATION_MEMBER,
            UserRole.ADMIN,
        ]

    def test_moderator_cannot_assign_admin(self, moderator):
        assert assignable_roles(moderator) == [
            UserRole.CITIZEN,
            UserRole.ASSOCIATION_MEMBER,
        ]

    def test_citizen_can_assign_nothing(self, citizen):
        assert assignable_roles(citizen) == []

    def test_anonymous_can_assign_nothing(self):
        assert assignable_roles(None) == []

    def test_can_assign_role(self, admin, moderator):
        assert can_assign_role(admin, UserRole.ADMIN)
        assert not can_assign_role(moderator, UserRole.ADMIN)
        assert can_assign_role(moderator, UserRole.CITIZEN)


@pytest.mark.django_db
class TestCanChangeRole:
    def test_unchanged_role_always_allowed(self, moderator):
        # Even though a moderator cannot otherwise touch an admin.
        assert can_change_role(moderator, UserRole.ADMIN, UserRole.ADMIN)

    def test_admin_can_promote_to_admin(self, admin):
        assert can_change_role(admin, UserRole.CITIZEN, UserRole.ADMIN)

    def test_moderator_cannot_promote_to_admin(self, moderator):
        assert not can_change_role(moderator, UserRole.CITIZEN, UserRole.ADMIN)

    def test_moderator_can_swap_citizen_and_member(self, moderator):
        assert can_change_role(moderator, UserRole.CITIZEN, UserRole.ASSOCIATION_MEMBER)
        assert can_change_role(moderator, UserRole.ASSOCIATION_MEMBER, UserRole.CITIZEN)

    def test_moderator_cannot_demote_admin(self, moderator):
        # No authority over an existing admin user.
        assert not can_change_role(moderator, UserRole.ADMIN, UserRole.CITIZEN)


# --- edit form --------------------------------------------------------------


@pytest.mark.django_db
class TestRoleUserEditForm:
    def test_moderator_role_choices_exclude_admin(self, moderator, citizen):
        form = RoleUserEditForm(instance=citizen, for_user=moderator)
        values = [value for value, _ in form.fields["role"].choices]
        assert values == [UserRole.CITIZEN, UserRole.ASSOCIATION_MEMBER]

    def test_admin_role_choices_include_admin(self, admin, citizen):
        form = RoleUserEditForm(instance=citizen, for_user=admin)
        values = [value for value, _ in form.fields["role"].choices]
        assert UserRole.ADMIN in values

    def test_moderator_choices_locked_for_admin_target(self, moderator, admin):
        form = RoleUserEditForm(instance=admin, for_user=moderator)
        values = [value for value, _ in form.fields["role"].choices]
        assert values == [UserRole.ADMIN]

    def test_admin_can_promote_user_to_admin(self, admin, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, role=UserRole.ADMIN),
            instance=citizen,
            for_user=admin,
        )
        assert form.is_valid(), form.errors
        form.save()
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ADMIN

    def test_superuser_can_promote_user_to_admin(self, superuser, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, role=UserRole.ADMIN),
            instance=citizen,
            for_user=superuser,
        )
        assert form.is_valid(), form.errors

    def test_moderator_cannot_promote_user_to_admin(self, moderator, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, role=UserRole.ADMIN),
            instance=citizen,
            for_user=moderator,
        )
        assert not form.is_valid()
        assert "role" in form.errors

    def test_moderator_can_set_association_member(self, moderator, citizen):
        form = RoleUserEditForm(
            data=edit_post_data(citizen, role=UserRole.ASSOCIATION_MEMBER),
            instance=citizen,
            for_user=moderator,
        )
        assert form.is_valid(), form.errors
        form.save()
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ASSOCIATION_MEMBER

    def test_moderator_cannot_demote_admin(self, moderator, admin):
        form = RoleUserEditForm(
            data=edit_post_data(admin, role=UserRole.CITIZEN),
            instance=admin,
            for_user=moderator,
        )
        assert not form.is_valid()
        assert "role" in form.errors

    def test_moderator_may_save_admin_without_changing_role(self, moderator, admin):
        form = RoleUserEditForm(
            data=edit_post_data(admin, role=UserRole.ADMIN, first_name="Renamed"),
            instance=admin,
            for_user=moderator,
        )
        assert form.is_valid(), form.errors


# --- creation form ----------------------------------------------------------


@pytest.mark.django_db
class TestRoleUserCreationForm:
    def _create_data(self, **overrides: object) -> dict:
        data: dict[str, object] = {
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": UserRole.CITIZEN,
            "password1": "SomePass12345",
            "password2": "SomePass12345",
        }
        data.update(overrides)
        return data

    def test_moderator_cannot_create_admin(self, moderator):
        form = RoleUserCreationForm(data=self._create_data(role=UserRole.ADMIN), for_user=moderator)
        assert not form.is_valid()
        assert "role" in form.errors

    def test_admin_can_create_admin(self, admin):
        form = RoleUserCreationForm(data=self._create_data(role=UserRole.ADMIN), for_user=admin)
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.role == UserRole.ADMIN


# --- end-to-end through the Wagtail admin ----------------------------------


@pytest.mark.django_db
class TestUserAdminIntegration:
    def _grant_user_admin(self, user: User) -> None:
        user.is_staff = True
        user.save()
        perms = Permission.objects.filter(
            content_type__app_label="wagtailadmin", codename="access_admin"
        ) | Permission.objects.filter(
            content_type__app_label="core",
            codename__in=["add_user", "change_user", "delete_user"],
        )
        user.user_permissions.add(*perms)

    def test_role_field_rendered_in_edit_form(self, client, superuser, citizen):
        client.force_login(superuser)
        response = client.get(reverse("wagtailusers_users:edit", args=[citizen.pk]))
        assert response.status_code == 200
        assert b'name="role"' in response.content

    def test_superuser_can_change_role_via_admin(self, client, superuser, citizen):
        client.force_login(superuser)
        response = client.post(
            reverse("wagtailusers_users:edit", args=[citizen.pk]),
            data=edit_post_data(citizen, role=UserRole.ADMIN),
        )
        assert response.status_code == 302
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ADMIN

    def test_moderator_cannot_escalate_role_via_admin(self, client, moderator, citizen):
        self._grant_user_admin(moderator)
        client.force_login(moderator)
        response = client.post(
            reverse("wagtailusers_users:edit", args=[citizen.pk]),
            data=edit_post_data(citizen, role=UserRole.ADMIN),
        )
        # Form re-renders with an error rather than redirecting.
        assert response.status_code == 200
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN

    def test_moderator_can_set_member_via_admin(self, client, moderator, citizen):
        self._grant_user_admin(moderator)
        client.force_login(moderator)
        response = client.post(
            reverse("wagtailusers_users:edit", args=[citizen.pk]),
            data=edit_post_data(citizen, role=UserRole.ASSOCIATION_MEMBER),
        )
        assert response.status_code == 302
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ASSOCIATION_MEMBER
