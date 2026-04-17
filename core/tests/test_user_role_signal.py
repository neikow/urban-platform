import pytest
from django.contrib.auth.models import Group

from core.models import User, UserRole


@pytest.fixture
def editors_group(db):
    group, _ = Group.objects.get_or_create(name="Editors")
    return group


@pytest.fixture
def moderators_group(db):
    group, _ = Group.objects.get_or_create(name="Moderators")
    return group


@pytest.fixture
def other_group(db):
    group, _ = Group.objects.get_or_create(name="OtherGroup")
    return group


@pytest.fixture
def citizen(db):
    return User.objects.create_user(email="citizen@example.com", password="pass123")


@pytest.mark.django_db
class TestSyncRoleWithGroups:
    def test_initial_role_is_citizen(self, citizen):
        assert citizen.role == UserRole.CITIZEN

    def test_adding_editors_group_sets_association_member(self, citizen, editors_group):
        citizen.groups.add(editors_group)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ASSOCIATION_MEMBER

    def test_adding_moderators_group_sets_association_member(self, citizen, moderators_group):
        citizen.groups.add(moderators_group)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ASSOCIATION_MEMBER

    def test_removing_last_privileged_group_reverts_to_citizen(self, citizen, editors_group):
        citizen.groups.add(editors_group)
        citizen.groups.remove(editors_group)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN

    def test_removing_one_privileged_group_keeps_role_when_another_remains(
        self, citizen, editors_group, moderators_group
    ):
        citizen.groups.set([editors_group, moderators_group])
        citizen.groups.remove(editors_group)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ASSOCIATION_MEMBER

    def test_clearing_all_groups_reverts_to_citizen(self, citizen, editors_group):
        citizen.groups.add(editors_group)
        citizen.groups.clear()
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN

    def test_non_privileged_group_does_not_promote_role(self, citizen, other_group):
        citizen.groups.add(other_group)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN

    def test_admin_role_is_never_changed(self, db, editors_group):
        admin = User.objects.create_user(
            email="admin@example.com", password="pass123", role=UserRole.ADMIN
        )
        admin.groups.add(editors_group)
        admin.refresh_from_db()
        assert admin.role == UserRole.ADMIN

    def test_admin_role_not_reverted_on_group_remove(self, db, editors_group):
        admin = User.objects.create_user(
            email="admin2@example.com", password="pass123", role=UserRole.ADMIN
        )
        admin.groups.add(editors_group)
        admin.groups.remove(editors_group)
        admin.refresh_from_db()
        assert admin.role == UserRole.ADMIN

    def test_adding_from_group_side_sets_association_member(self, citizen, editors_group):
        editors_group.user_set.add(citizen)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.ASSOCIATION_MEMBER

    def test_removing_from_group_side_reverts_to_citizen(self, citizen, editors_group):
        editors_group.user_set.add(citizen)
        editors_group.user_set.remove(citizen)
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN
