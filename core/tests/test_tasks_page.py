from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone

from core import task_monitor
from core.models import TaskRun, TaskRunStatus, User, UserRole
from core.task_monitor import LiveState, LiveTask, live_state, prune_runs
from core.tasks import prune_task_runs


def make_run(**fields):
    defaults = {
        "task_id": f"id-{TaskRun.objects.count()}",
        "name": "core.tasks.prune_task_runs",
        "started_at": timezone.now(),
    }
    return TaskRun.objects.create(**{**defaults, **fields})


@pytest.mark.django_db
class TestHistory:
    def test_successful_run_is_recorded(self):
        prune_task_runs.delay()

        run = TaskRun.objects.get()
        assert run.name == "core.tasks.prune_task_runs"
        assert run.status == TaskRunStatus.SUCCESS
        assert run.result == "0"
        assert run.finished_at is not None
        assert run.duration_seconds is not None

    def test_failed_run_keeps_the_error(self):
        # apply(throw=False) runs the worker's code path (eager mode skips failure signals).
        with patch("core.task_monitor.prune_runs", side_effect=ValueError("boom")):
            prune_task_runs.apply(throw=False)

        run = TaskRun.objects.get()
        assert run.status == TaskRunStatus.FAILURE
        assert run.error == "ValueError: boom"

    def test_arguments_are_summarised(self):
        from publications.tasks import refresh_map_tiles

        with patch("publications.map_tiles.refresh_tiles", return_value=None):
            refresh_map_tiles.delay(force=True)

        assert TaskRun.objects.get().arguments == "force=True"

    def test_monitoring_errors_do_not_fail_the_task(self):
        with patch.object(TaskRun.objects, "update_or_create", side_effect=DatabaseError):
            assert prune_task_runs.delay().get() == 0

    def test_old_runs_are_pruned(self):
        old = make_run(started_at=timezone.now() - timedelta(days=31))
        recent = make_run()

        assert prune_runs() == 1
        assert list(TaskRun.objects.all()) == [recent]
        assert not TaskRun.objects.filter(pk=old.pk).exists()


class TestLiveState:
    @pytest.fixture(autouse=True)
    def broker(self):
        with patch.object(task_monitor, "_queue_length", return_value=2):
            yield

    def inspector(self, ping=None, active=None, reserved=None, scheduled=None):
        inspector = MagicMock()
        inspector.ping.return_value = ping
        inspector.active.return_value = active
        inspector.reserved.return_value = reserved
        inspector.scheduled.return_value = scheduled
        return inspector

    def test_parses_worker_replies(self):
        inspector = self.inspector(
            ping={"celery@w1": {"ok": "pong"}},
            active={
                "celery@w1": [
                    {
                        "id": "a",
                        "name": "core.tasks.reassign_residents",
                        "args": [],
                        "kwargs": {},
                        "time_start": 1_790_000_000.0,
                    }
                ]
            },
            reserved={
                "celery@w1": [
                    {
                        "id": "b",
                        "name": "publications.tasks.close_expired_polls",
                        "args": [3],
                        "kwargs": {},
                    }
                ]
            },
            scheduled={
                "celery@w1": [
                    {
                        "eta": "2026-10-08T12:00:00+02:00",
                        "request": {
                            "id": "c",
                            "name": "core.emails.tasks.send",
                            "args": [],
                            "kwargs": {"user_id": 4},
                        },
                    }
                ]
            },
        )
        with patch("urban_platform.celery.app.control.inspect", return_value=inspector):
            state = task_monitor._inspect()

        assert state.reachable
        assert state.workers == ["celery@w1"]
        assert state.queued == 2
        assert [(t.id, t.state) for t in state.tasks] == [
            ("a", "active"),
            ("b", "reserved"),
            ("c", "scheduled"),
        ]
        assert state.tasks[0].started_at is not None
        assert state.tasks[1].arguments == "3"
        assert state.tasks[2].arguments == "user_id=4"
        assert state.tasks[2].eta is not None
        assert state.running("core.tasks.reassign_residents")

    def test_no_worker(self):
        with patch(
            "urban_platform.celery.app.control.inspect", return_value=self.inspector(ping=None)
        ):
            state = task_monitor._inspect()

        assert not state.reachable
        assert state.queued == 2

    def test_broker_down(self):
        with patch.object(task_monitor, "_inspect", side_effect=ConnectionError):
            assert not live_state().reachable


class TestQueueLength:
    def channel(self, **behaviour):
        connection = MagicMock()
        connection.__enter__.return_value.default_channel.queue_declare = MagicMock(**behaviour)
        return patch("urban_platform.celery.app.connection_for_read", return_value=connection)

    def test_counts_waiting_messages(self):
        with self.channel(return_value=MagicMock(message_count=7)):
            assert task_monitor._queue_length() == 7

    def test_missing_queue_is_empty(self):
        from amqp.exceptions import ChannelError

        with self.channel(side_effect=ChannelError(reply_text="NOT_FOUND", reply_code="404")):
            assert task_monitor._queue_length() == 0

    def test_broker_down_hides_the_count(self):
        with self.channel(side_effect=ConnectionError):
            assert task_monitor._queue_length() is None


@pytest.fixture
def online():
    """One idle worker."""
    with patch.object(
        task_monitor,
        "live_state",
        return_value=LiveState(reachable=True, workers=["celery@w1"], queued=0),
    ):
        yield


@pytest.fixture
def admin_client(client, db):
    client.force_login(
        User.objects.create_user(email="admin@example.com", password="x", role=UserRole.ADMIN)
    )
    return client


@pytest.mark.django_db
class TestTasksPage:
    def test_page_lists_triggers_runs_and_polls(self, admin_client, online):
        make_run(status=TaskRunStatus.FAILURE, error="ValueError: boom")

        content = admin_client.get(reverse("admin_tasks")).content.decode()

        assert 'id="tasks-status"' in content
        assert f'data-url="{reverse("admin_tasks_status")}"' in content
        assert "dist/admin-tasks.js" in content
        assert "ValueError: boom" in content
        for trigger in task_monitor.TRIGGERS:
            assert reverse("admin_tasks_run", args=[trigger.key]) in content

    def test_status_fragment(self, admin_client):
        live = LiveState(
            reachable=True,
            workers=["celery@w1"],
            tasks=[
                LiveTask(
                    id="a",
                    name="core.tasks.reassign_residents",
                    arguments="",
                    worker="celery@w1",
                    state="active",
                )
            ],
        )
        with patch.object(task_monitor, "live_state", return_value=live):
            response = admin_client.get(reverse("admin_tasks_status"))

        content = response.content.decode()
        assert "<html" not in content
        assert "core.tasks.reassign_residents" in content
        assert "no-cache" in response["Cache-Control"]

    def test_status_without_worker(self, admin_client):
        with patch.object(task_monitor, "live_state", return_value=LiveState(reachable=False)):
            content = admin_client.get(reverse("admin_tasks_status")).content.decode()

        assert "tasks-status--failure" in content

    @pytest.mark.parametrize("role", [UserRole.ASSOCIATION_MEMBER, UserRole.CITIZEN])
    def test_reserved_to_administrators(self, client, role):
        client.force_login(User.objects.create_user(email="u@example.com", password="x", role=role))

        for url in (reverse("admin_tasks"), reverse("admin_tasks_status")):
            assert client.get(url).status_code in (302, 403)
        assert client.post(reverse("admin_tasks_run", args=["residents"])).status_code in (302, 403)

    def test_menu_entry_for_administrators(self, admin_client, online):
        content = admin_client.get(reverse("wagtailadmin_home")).content.decode()

        assert reverse("admin_tasks") in content

    def test_run_trigger(self, admin_client, online, django_capture_on_commit_callbacks):
        with patch("core.tasks.reassign_residents.delay") as delay:
            response = admin_client.post(reverse("admin_tasks_run", args=["residents"]))

        assert response.status_code == 302
        delay.assert_called_once_with()

    def test_trigger_already_running(self, admin_client):
        live = LiveState(
            reachable=True,
            tasks=[
                LiveTask(
                    id="a",
                    name="core.tasks.reassign_residents",
                    arguments="",
                    worker="w",
                    state="active",
                )
            ],
        )
        with (
            patch.object(task_monitor, "live_state", return_value=live),
            patch("core.tasks.reassign_residents.delay") as delay,
        ):
            admin_client.post(reverse("admin_tasks_run", args=["residents"]))

        delay.assert_not_called()

    def test_unknown_trigger(self, admin_client):
        assert admin_client.post(reverse("admin_tasks_run", args=["nope"])).status_code == 404

    def test_triggers_need_post(self, admin_client):
        assert admin_client.get(reverse("admin_tasks_run", args=["residents"])).status_code == 405
