"""Background tasks seen from the admin (Settings › Tasks).

- History: every Celery task run is recorded as a TaskRun by the signal
  receivers below, connected in CoreConfig.ready().
- Live: what the workers are running, have reserved or scheduled (Celery's
  remote inspection), and how many messages wait in the broker queue.
- Triggers: a short list of tasks that are safe to run at any time.

The page polls a fragment of this state every few seconds (core.views.tasks).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.core.cache import cache
from django.db import DatabaseError
from django.utils import timezone
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30
HISTORY_SIZE = 50
# How long workers get to answer an inspection, and how long the answer is reused.
INSPECT_TIMEOUT = 1.0
LIVE_CACHE_KEY = "task-monitor:live"
LIVE_CACHE_SECONDS = 3
SUMMARY_LENGTH = 255


def _truncate(text: str) -> str:
    return text if len(text) <= SUMMARY_LENGTH else text[: SUMMARY_LENGTH - 1] + "…"


def _summary(value: Any) -> str:
    return _truncate(repr(value))


def _arguments(args: Any, kwargs: Any) -> str:
    parts = [repr(a) for a in args or ()] + [f"{k}={v!r}" for k, v in (kwargs or {}).items()]
    return _truncate(", ".join(parts))


# --- history (Celery signal receivers) ------------------------------------------


def on_task_prerun(task_id: str, task: Any, args: Any = None, kwargs: Any = None, **_: Any) -> None:
    from core.models import TaskRun, TaskRunStatus

    try:
        TaskRun.objects.update_or_create(
            task_id=task_id,
            defaults={
                "name": task.name,
                "arguments": _arguments(args, kwargs),
                "status": TaskRunStatus.STARTED,
                "worker": getattr(task.request, "hostname", None) or "",
                "started_at": timezone.now(),
                "finished_at": None,
                "result": "",
                "error": "",
            },
        )
    except DatabaseError:
        # Monitoring must never make a task fail.
        logger.exception("Could not record the start of task %s", task_id)


def on_task_postrun(task_id: str, retval: Any = None, state: str | None = None, **_: Any) -> None:
    from core.models import TaskRun, TaskRunStatus

    status = state if state in TaskRunStatus.values else TaskRunStatus.SUCCESS
    fields: dict[str, Any] = {"status": status, "finished_at": timezone.now()}
    if status == TaskRunStatus.SUCCESS:
        fields["result"] = "" if retval is None else _summary(retval)
    try:
        TaskRun.objects.filter(task_id=task_id).update(**fields)
    except DatabaseError:
        logger.exception("Could not record the end of task %s", task_id)


def on_task_failure(task_id: str, exception: BaseException | None = None, **_: Any) -> None:
    from core.models import TaskRun

    error = f"{type(exception).__name__}: {exception}" if exception else ""
    try:
        TaskRun.objects.filter(task_id=task_id).update(error=error[:2000])
    except DatabaseError:
        logger.exception("Could not record the failure of task %s", task_id)


def connect_signals() -> None:
    from celery.signals import task_failure, task_postrun, task_prerun

    task_prerun.connect(on_task_prerun, dispatch_uid="core.task_monitor.prerun", weak=False)
    task_postrun.connect(on_task_postrun, dispatch_uid="core.task_monitor.postrun", weak=False)
    task_failure.connect(on_task_failure, dispatch_uid="core.task_monitor.failure", weak=False)


def prune_runs() -> int:
    """Delete runs older than RETENTION_DAYS. Returns how many."""
    from core.models import TaskRun

    cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
    deleted, _counts = TaskRun.objects.filter(started_at__lt=cutoff).delete()
    return deleted


def recent_runs() -> list[Any]:
    from core.models import TaskRun

    return list(TaskRun.objects.all()[:HISTORY_SIZE])


# --- live state (Celery remote inspection) --------------------------------------


@dataclass
class LiveTask:
    id: str
    name: str
    arguments: str
    worker: str
    state: str  # "active", "reserved" or "scheduled"
    started_at: datetime | None = None
    eta: datetime | None = None


@dataclass
class LiveState:
    reachable: bool
    workers: list[str] = field(default_factory=list)
    tasks: list[LiveTask] = field(default_factory=list)
    queued: int | None = None  # messages waiting in the broker, not yet taken by a worker
    checked_at: datetime = field(default_factory=timezone.now)

    def running(self, name: str) -> bool:
        return any(t.name == name for t in self.tasks)


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=timezone.get_current_timezone())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _inspect() -> LiveState:
    from urban_platform.celery import app

    # A broadcast waits its whole timeout for unknown workers. Ping once, then ask
    # only the workers that answered: each call returns as soon as they all reply.
    control: Any = app.control
    pings = control.inspect(timeout=INSPECT_TIMEOUT).ping() or {}
    if not pings:
        return LiveState(reachable=False, queued=_queue_length())
    inspector = control.inspect(destination=list(pings), limit=len(pings), timeout=INSPECT_TIMEOUT)

    tasks: list[LiveTask] = []
    for state, replies in (
        ("active", inspector.active() or {}),
        ("reserved", inspector.reserved() or {}),
        ("scheduled", inspector.scheduled() or {}),
    ):
        for worker, entries in replies.items():
            for entry in entries:
                request = entry.get("request", entry)  # scheduled entries wrap the request
                tasks.append(
                    LiveTask(
                        id=request.get("id", ""),
                        name=request.get("name") or request.get("type", ""),
                        arguments=_arguments(request.get("args"), request.get("kwargs")),
                        worker=worker,
                        state=state,
                        started_at=_timestamp(request.get("time_start")),
                        eta=_timestamp(entry.get("eta")),
                    )
                )
    return LiveState(reachable=True, workers=sorted(pings), tasks=tasks, queued=_queue_length())


def _queue_length() -> int | None:
    from urban_platform.celery import app

    from amqp.exceptions import ChannelError

    try:
        with app.connection_for_read() as connection:
            declared = connection.default_channel.queue_declare(
                queue=app.conf.task_default_queue, passive=True
            )
        return int(declared.message_count)
    except ChannelError as error:
        # Redis deletes an empty list: "no queue" (404) means nothing waiting.
        if str(getattr(error, "reply_code", "")) == "404":
            return 0
        return None
    except Exception:  # noqa: BLE001 — any broker trouble just hides the count
        return None


def live_state() -> LiveState:
    """The workers' current tasks, shared by every admin for a few seconds."""
    cached = cache.get(LIVE_CACHE_KEY)
    if isinstance(cached, LiveState):
        return cached
    try:
        state = _inspect()
    except Exception:  # noqa: BLE001 — an unreachable broker is a state to show
        logger.warning("Could not inspect the Celery workers", exc_info=True)
        state = LiveState(reachable=False)
    cache.set(LIVE_CACHE_KEY, state, LIVE_CACHE_SECONDS)
    return state


# --- manual triggers ------------------------------------------------------------


@dataclass(frozen=True)
class Trigger:
    key: str
    label: str | Promise
    description: str | Promise
    task_name: str
    start: Callable[[], bool]  # False when it was already under way


def _start_map_tiles() -> bool:
    from publications.map_tiles import queue_refresh

    return queue_refresh()


def _starter(task_path: str) -> Callable[[], bool]:
    def start() -> bool:
        from celery import current_app

        if live_state().running(task_path):
            return False
        current_app.tasks[task_path].delay()
        return True

    return start


TRIGGERS = (
    Trigger(
        "map_tiles",
        _("Update the map"),
        _("Download the latest OpenStreetMap data for the maps (about 35 MB)."),
        "publications.tasks.refresh_map_tiles",
        _start_map_tiles,
    ),
    Trigger(
        "residents",
        _("Match residents to associations"),
        _("Attach every user with an address to the association whose area contains it."),
        "core.tasks.reassign_residents",
        _starter("core.tasks.reassign_residents"),
    ),
    Trigger(
        "close_polls",
        _("Close expired polls"),
        _("Close the votes whose end date has passed, and send their results."),
        "publications.tasks.close_expired_polls",
        _starter("publications.tasks.close_expired_polls"),
    ),
)


def get_trigger(key: str) -> Trigger | None:
    return next((t for t in TRIGGERS if t.key == key), None)
