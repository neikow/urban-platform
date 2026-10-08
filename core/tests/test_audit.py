import csv
import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from wagtail.models import ModelLogEntry, PageLogEntry

from core import audit, task_monitor
from core.models import FeatureFlags, TaskRun, User, UserRole
from core.task_monitor import LiveState
from core.tests.test_user_role_admin import edit_post_data
from home.models import HomePage
from publications.models import (
    ParticipationMode,
    PollClosureReason,
    ProjectPage,
    PublicationIndexPage,
)
from publications.polls import close_poll


def make_user(role: str, email: str, **fields: object) -> User:
    return User.objects.create_user(
        email=email, password="Pass12345", first_name="First", last_name="Last", role=role, **fields
    )


def entries(instance, action: str | None = None):
    found = ModelLogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(instance, for_concrete_model=False),
        object_id=str(instance.pk),
    )
    return found.filter(action=action) if action else found


@pytest.fixture
def admin(db):
    return make_user(UserRole.ADMIN, "admin@example.com")


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


# --- account changes --------------------------------------------------------------


@pytest.mark.django_db
class TestAccountChanges:
    def test_role_change_in_the_admin_names_who_did_it(self, client, admin):
        citizen = make_user(UserRole.CITIZEN, "citizen@example.com")
        client.force_login(admin)

        client.post(
            reverse("wagtailusers_users:edit", args=[citizen.pk]),
            edit_post_data(citizen, role=UserRole.MODERATOR, is_subscriber="on"),
        )

        role = entries(citizen, "core.user.role_change").get()
        assert role.user == admin
        assert role.data == {"old": UserRole.CITIZEN, "new": UserRole.MODERATOR}
        assert entries(citizen, "core.user.subscription_change").get().data["new"] is True
        # Wagtail's own entry for the edit is still there.
        assert entries(citizen, "wagtail.edit").exists()

    def test_deactivation_and_superuser(self, admin):
        user = make_user(UserRole.EDITOR, "editor@example.com")

        user.is_active = False
        user.is_superuser = True
        user.save()

        assert entries(user, "core.user.activation_change").get().data["new"] is False
        assert entries(user, "core.user.superuser_change").get().data["new"] is True

    def test_new_staff_account(self, db):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        citizen = make_user(UserRole.CITIZEN, "citizen@example.com")

        assert entries(editor, "core.user.role_change").get().data == {
            "old": None,
            "new": UserRole.EDITOR,
        }
        assert not entries(citizen).exists()

    def test_other_saves_are_not_logged(self, db):
        user = make_user(UserRole.EDITOR, "editor@example.com")
        before = entries(user).count()

        user.first_name = "Renamed"
        user.save()
        User.objects.only("pk").get(pk=user.pk).save()  # deferred fields: no crash, no entry

        assert entries(user).count() == before


# --- security events --------------------------------------------------------------


@pytest.mark.django_db
class TestSecurityEvents:
    def test_staff_logins(self, client):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        citizen = make_user(UserRole.CITIZEN, "citizen@example.com")

        client.login(email=editor.email, password="Pass12345")
        client.login(email=citizen.email, password="Pass12345")

        assert entries(editor, "core.auth.login").get().user == editor
        assert not entries(citizen, "core.auth.login").exists()

    def test_failed_logins_on_staff_accounts(self, client):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        citizen = make_user(UserRole.CITIZEN, "citizen@example.com")

        client.login(email=editor.email, password="wrong")
        client.login(email=citizen.email, password="wrong")
        client.login(email="nobody@example.com", password="wrong")

        failed = entries(editor, "core.auth.login_failed").get()
        assert failed.user is None
        assert not entries(citizen, "core.auth.login_failed").exists()

    def test_password_change(self, client):
        user = make_user(UserRole.CITIZEN, "citizen@example.com")
        client.force_login(user)

        client.post(
            reverse("password_change"),
            {
                "current_password": "Pass12345",
                "new_password": "NewSecret123",
                "confirm_password": "NewSecret123",
            },
        )

        assert entries(user, "core.auth.password_change").get().user == user

    def test_email_change(self, client):
        user = make_user(UserRole.CITIZEN, "citizen@example.com", postal_code="13007")
        client.force_login(user)

        with patch("core.views.profile_edit.send_verification_email"):
            client.post(
                reverse("profile_edit"),
                {
                    "email": "new@example.com",
                    "first_name": "First",
                    "last_name": "Last",
                    "postal_code": "13007",
                },
            )

        assert entries(user, "core.auth.email_change").get().data == {
            "old": "citizen@example.com",
            "new": "new@example.com",
        }

    def test_data_export(self, client):
        user = make_user(UserRole.CITIZEN, "citizen@example.com")
        client.force_login(user)

        response = client.get(reverse("data_export"))

        assert entries(user, "core.auth.data_export").exists()
        assert "account_activity" in response.json()

    def test_account_deletion_forgets_the_email(self, client):
        user = make_user(UserRole.EDITOR, "editor@example.com")
        client.login(email=user.email, password="Pass12345")
        audit.audit(
            user, "core.auth.email_change", user=user, old="old@example.com", new=user.email
        )

        client.post(reverse("account_delete"), {"password": "Pass12345", "confirm": "on"})

        user = User.objects.with_deleted().get(pk=user.pk)
        assert entries(user, "core.auth.account_delete").exists()
        assert not entries(user).filter(label__contains="editor@example.com").exists()
        assert entries(user, "core.auth.email_change").get().data == {}

    def test_old_security_events_are_pruned(self):
        user = make_user(UserRole.EDITOR, "editor@example.com")
        audit.audit(user, "core.auth.login", user=user)
        entries(user, "core.auth.login").update(timestamp=timezone.now() - timedelta(days=400))
        role = entries(user, "core.user.role_change").get()
        entries(user).filter(pk=role.pk).update(timestamp=timezone.now() - timedelta(days=400))

        assert audit.prune_security_events() == 1
        assert entries(user, "core.user.role_change").exists()


# --- tasks, settings, publications ------------------------------------------------


@pytest.mark.django_db
class TestOtherActions:
    def test_task_launch(self, client, admin):
        client.force_login(admin)
        idle = LiveState(reachable=True, workers=["w"])

        with patch.object(task_monitor, "live_state", return_value=idle):
            client.post(reverse("admin_tasks_run", args=["residents"]))

        run = TaskRun.objects.get(name="core.tasks.reassign_residents")
        assert run.launched_by == admin
        launch = entries(run, "core.task.launch").get()
        assert launch.user == admin
        assert launch.data["task"] == "core.tasks.reassign_residents"

    def test_settings_changes(self, client, admin):
        client.force_login(admin)
        flags = FeatureFlags.load()

        client.post(
            reverse("wagtailsettings:edit", args=["core", "featureflags", flags.pk]),
            {"participation_requires_subscription": "on"},
        )

        change = entries(flags, "core.settings.change").get()
        assert change.user == admin
        assert list(change.data["changes"].values()) == [[False, True]]

    def test_poll_closing(self, index, admin):
        project = ProjectPage(
            title="Square", slug="square", participation_mode=ParticipationMode.VOTING
        )
        index.add_child(instance=project)
        project.save_revision().publish()

        close_poll(project, PollClosureReason.MANUAL, closed_by=admin)
        close_poll(project, PollClosureReason.MANUAL, closed_by=admin)  # idempotent

        closing = PageLogEntry.objects.get(page=project, action="publications.poll.close")
        assert closing.user == admin and closing.data["reason"] == "MANUAL"

    def test_page_workflow_is_logged_by_wagtail(self, index):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        page = ProjectPage(title="Brouillon", slug="brouillon", live=False, description="d")
        index.add_child(instance=page)
        page.save_revision(user=editor, log_action=True)
        page.get_workflow().start(page, editor)

        actions = set(PageLogEntry.objects.filter(page=page).values_list("action", flat=True))
        assert {"wagtail.edit", "wagtail.workflow.start"} <= actions


# --- the activity log page --------------------------------------------------------


@pytest.mark.django_db
class TestActivityLogPage:
    def test_administrators_only(self, client, admin):
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")

        client.force_login(moderator)
        assert client.get(reverse("audit_log")).status_code in (302, 403)
        client.force_login(admin)
        assert client.get(reverse("audit_log")).status_code == 200

    def test_menu_entry(self, client, admin):
        client.force_login(admin)

        assert reverse("audit_log") in client.get(reverse("wagtailadmin_home")).content.decode()

    def test_filter_by_action(self, client, admin):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        audit.audit(editor, "core.auth.password_change", user=editor)
        client.force_login(admin)

        content = client.get(
            reverse("audit_log_results"), {"action": "core.auth.password_change"}
        ).content.decode()

        assert "editor@example.com" in content
        assert "admin@example.com" not in content

    def test_csv_export_has_the_details(self, client, admin):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        client.force_login(admin)

        response = client.get(
            reverse("audit_log"), {"export": "csv", "action": "core.user.role_change"}
        )

        assert response.status_code == 200
        assert "journal-activite" in response["Content-Disposition"]
        rows = list(csv.reader(io.StringIO(b"".join(response.streaming_content).decode())))
        header, *lines = rows
        assert len(header) == 7
        assert any(editor.email in line for line in lines)
        details = header.index(header[-1])
        assert all(line[details] for line in lines)
