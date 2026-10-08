import csv
import io
from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone

from core.models import Membership, User, UserRole

TODAY = timezone.localdate


def make_user(role: str, email: str) -> User:
    return User.objects.create_user(
        email=email, password="pass12345", first_name="First", last_name="Last", role=role
    )


@pytest.fixture
def admin(db):
    return make_user(UserRole.ADMIN, "admin@example.com")


@pytest.fixture
def resident(db):
    return make_user(UserRole.CITIZEN, "resident@example.com")


@pytest.mark.django_db
class TestMembershipModel:
    def test_running_memberships(self, resident):
        today = TODAY()
        ended = Membership.objects.create(
            user=resident, starts_on=today - timedelta(days=60), ends_on=today - timedelta(days=1)
        )
        future = Membership.objects.create(user=resident, starts_on=today + timedelta(days=1))
        assert not resident.is_member
        assert not ended.is_active and not future.is_active

        running = Membership.objects.create(user=resident, ends_on=today)

        assert running.is_active
        assert resident.is_member
        assert list(Membership.objects.active()) == [running]

    def test_open_ended(self, resident):
        Membership.objects.create(user=resident, starts_on=TODAY() - timedelta(days=900))

        assert resident.is_member

    def test_unsaved_users_are_not_members(self):
        assert not User(email="new@example.com").is_member

    def test_end_before_start_is_refused(self, resident):
        membership = Membership(user=resident, starts_on=TODAY(), ends_on=TODAY() - timedelta(1))

        with pytest.raises(Exception) as error:
            membership.full_clean()
        assert "ends_on" in error.value.message_dict  # type: ignore[attr-defined]

    def test_account_deletion_ends_running_memberships(self, resident):
        membership = Membership.objects.create(user=resident, starts_on=TODAY() - timedelta(30))

        resident.soft_delete()

        membership.refresh_from_db()
        assert membership.ends_on == TODAY()

    def test_personal_data_export(self, client, resident):
        Membership.objects.create(user=resident, note="Espèces")
        client.force_login(resident)

        data = client.get(reverse("data_export")).json()

        assert data["account"]["memberships"] == [
            {"starts_on": TODAY().isoformat(), "ends_on": None, "note": "Espèces"}
        ]


@pytest.mark.django_db
class TestMembershipAdmin:
    def test_administrators_only(self, client, admin):
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")

        client.force_login(moderator)
        assert client.get(reverse("membership:index")).status_code in (302, 403)
        client.force_login(admin)
        assert client.get(reverse("membership:index")).status_code == 200

    def test_record_from_the_user_page(self, client, admin, resident):
        client.force_login(admin)

        form = client.get(reverse("membership:add"), {"user": resident.pk}).content.decode()
        assert f'value="{resident.pk}"' in form

        response = client.post(
            reverse("membership:add"),
            {
                "user": resident.pk,
                "starts_on": TODAY().isoformat(),
                "ends_on": "",
                "note": "Chèque",
            },
        )

        assert response.status_code == 302
        membership = Membership.objects.get()
        assert membership.user == resident and membership.created_by == admin
        assert resident.is_member

    def test_end_before_start_in_the_form(self, client, admin, resident):
        client.force_login(admin)

        response = client.post(
            reverse("membership:add"),
            {
                "user": resident.pk,
                "starts_on": TODAY().isoformat(),
                "ends_on": (TODAY() - timedelta(days=1)).isoformat(),
            },
        )

        assert response.status_code == 200
        assert not Membership.objects.exists()

    def test_filter_running_and_search(self, client, admin, resident):
        other = make_user(UserRole.CITIZEN, "other@example.com")
        Membership.objects.create(user=resident)
        Membership.objects.create(
            user=other, starts_on=TODAY() - timedelta(400), ends_on=TODAY() - timedelta(35)
        )
        client.force_login(admin)

        running = client.get(reverse("membership:index"), {"running": "true"}).content.decode()
        assert "resident@example.com" in running and "other@example.com" not in running

        ended = client.get(reverse("membership:index"), {"running": "false"}).content.decode()
        assert "other@example.com" in ended and "resident@example.com" not in ended

        found = client.get(reverse("membership:index"), {"q": "other@"}).content.decode()
        assert "other@example.com" in found and "resident@example.com" not in found

    def test_csv_export(self, client, admin, resident):
        Membership.objects.create(user=resident, note="Virement")
        client.force_login(admin)

        response = client.get(reverse("membership:index"), {"export": "csv"})

        assert "adhesions" in response["Content-Disposition"]
        rows = list(csv.reader(io.StringIO(b"".join(response.streaming_content).decode())))
        assert any("resident@example.com" in row and "Virement" in row for row in rows[1:])

    def test_recording_is_in_the_activity_log(self, client, admin, resident):
        from wagtail.models import ModelLogEntry

        client.force_login(admin)
        client.post(
            reverse("membership:add"), {"user": resident.pk, "starts_on": TODAY().isoformat()}
        )

        entry = ModelLogEntry.objects.get(action="wagtail.create")
        assert entry.user == admin and "resident@example.com" in entry.label

    def test_user_chooser_searches_the_database(self, client, admin, resident):
        client.force_login(admin)

        content = client.get(
            reverse("user_chooser:choose_results"), {"q": "resident"}
        ).content.decode()

        assert "resident@example.com" in content
        assert "admin@example.com" not in content

    def test_user_page_links_to_memberships(self, client, admin, resident):
        Membership.objects.create(user=resident)
        client.force_login(admin)

        content = client.get(
            reverse("wagtailusers_users:edit", args=[resident.pk])
        ).content.decode()

        assert reverse("membership:index") in content
        assert f"{reverse('membership:add')}?user={resident.pk}" in content


@pytest.mark.django_db(transaction=True)
def test_migration_turns_subscribers_into_memberships():
    executor = MigrationExecutor(connection)
    executor.migrate([("core", "0018_audit_trail")])
    old_apps = executor.loader.project_state([("core", "0018_audit_trail")]).apps
    OldUser = old_apps.get_model("core", "User")
    since = timezone.now() - timedelta(days=10)
    subscriber = OldUser.objects.create(
        email="old@example.com", is_subscriber=True, subscribed_at=since, role="CITIZEN"
    )
    OldUser.objects.create(email="none@example.com", role="CITIZEN")

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())

    membership = Membership.objects.get()
    assert membership.user_id == subscriber.pk
    assert membership.starts_on == timezone.localdate(since)
    assert membership.ends_on is None
