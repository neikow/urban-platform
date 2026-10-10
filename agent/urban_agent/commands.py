"""One-off commands the control plane asks for a website: its logs, a restart, its
setup again, the first administrator's invitation again.

Only these, with checked arguments: the control plane names a command, never what
runs. Each runs once (its id is remembered in ``commands.json``) and its result is
reported until the control plane stops asking, that is once it has the result.
"""

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .docker import DockerError

logger = logging.getLogger(__name__)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
BACKUP_ID = re.compile(r"^\d{8}T\d{6}Z$")
BACKUP_FILES = ("db.dump", "media.tar.gz")
# Run by the backups' thread: their result comes later.
LONG = ("backup", "restore")
SERVICE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
OUTPUT_CHARS = 20_000
MAX_LOG_LINES = 1000
# Results kept after the control plane stopped asking: in case it asks again.
KEEP_SECONDS = 24 * 3600
TIMEOUT = 300
# The services that run (not the one-shot jobs).
LONG_RUNNING = ["web", "worker", "nginx"]
MANAGE = ["exec", "-T", "web", "python", "manage.py"]


class InvalidCommand(Exception):
    pass


@dataclass
class Command:
    id: int
    slug: str
    name: str
    args: dict[str, Any]

    @classmethod
    def parse(cls, data: Any) -> "Command":
        if not isinstance(data, dict):
            raise InvalidCommand("not an object")
        command_id, slug, name = data.get("id"), data.get("slug"), data.get("name")
        if not isinstance(command_id, int) or isinstance(command_id, bool) or command_id < 1:
            raise InvalidCommand(f"invalid command id {command_id!r}")
        if not isinstance(slug, str) or not SLUG.match(slug):
            raise InvalidCommand(f"command {command_id}: invalid slug {slug!r}")
        args = data.get("args") or {}
        if not isinstance(args, dict):
            raise InvalidCommand(f"command {command_id}: args is not an object")
        if name == "logs":
            service, lines = args.get("service", ""), args.get("lines", 200)
            if not isinstance(service, str) or (service and not SERVICE.match(service)):
                raise InvalidCommand(f"command {command_id}: invalid service {service!r}")
            if not isinstance(lines, int) or isinstance(lines, bool):
                raise InvalidCommand(f"command {command_id}: invalid lines {lines!r}")
            args = {"service": service, "lines": max(1, min(lines, MAX_LOG_LINES))}
        elif name in ("restart", "bootstrap", "invite_admin", "backup"):
            args = {}
        elif name == "restore":
            backup_id, urls = args.get("backup"), args.get("urls") or {}
            if not isinstance(backup_id, str) or not BACKUP_ID.match(backup_id):
                raise InvalidCommand(f"command {command_id}: invalid backup {backup_id!r}")
            if not isinstance(urls, dict) or (urls and set(urls) != set(BACKUP_FILES)):
                raise InvalidCommand(f"command {command_id}: urls must name {BACKUP_FILES}")
            if not all(isinstance(u, str) and u.startswith("https://") for u in urls.values()):
                raise InvalidCommand(f"command {command_id}: download links must be https")
            args = {"backup": backup_id, "urls": dict(urls)}
        else:
            raise InvalidCommand(f"command {command_id}: unknown command {name!r}")
        return cls(id=command_id, slug=slug, name=name, args=args)

    def compose_args(self) -> list[str]:
        if self.name == "logs":
            service = [self.args["service"]] if self.args["service"] else []
            return [
                "logs",
                "--no-color",
                "--timestamps",
                "--tail",
                str(self.args["lines"]),
                *service,
            ]
        if self.name == "restart":
            return ["restart", *LONG_RUNNING]
        if self.name == "bootstrap":
            return [*MANAGE, "bootstrap_tenant"]
        return [*MANAGE, "invite_admin"]


# What the journal says once a command that changes something has run.
DONE = {
    "restart": "Restarted, as the control plane asked.",
    "bootstrap": "Setup run again, as the control plane asked.",
    "invite_admin": "Administrator's invitation sent again, as the control plane asked.",
}


class Commands:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.results: dict[str, dict[str, Any]] = self._load()
        self.lock = threading.Lock()

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.results))

    def _finish(self, key: str, ok: bool, output: str) -> None:
        """The result of a command run by the backups' thread."""
        with self.lock:
            self.results[key].update(ok=ok, output=output[-OUTPUT_CHARS:])
        self._save()

    def run(
        self, asked: Any, reconciler: Any, errors: list[str], now: float | None = None
    ) -> list[dict[str, Any]]:
        """Run the commands not run yet; returns the results of all those asked. Invalid
        ones go to ``errors``."""
        now = time.time() if now is None else now
        reported = []
        changed = False
        for data in asked if isinstance(asked, list) else []:
            try:
                command = Command.parse(data)
            except InvalidCommand as error:
                errors.append(str(error))
                continue
            key = str(command.id)
            if key not in self.results:
                changed = True
                if command.name in LONG:
                    self.results[key] = {"ok": None, "output": "", "at": now}
                    self.start(key, command, reconciler)
                else:
                    ok, output = self.execute(command, reconciler)
                    self.results[key] = {"ok": ok, "output": output, "at": now}
                    if ok and command.name in DONE:
                        reconciler.journal.record("info", DONE[command.name], command.slug)
            result = self.results[key]
            if result["ok"] is None:
                continue  # still running: reported once done
            reported.append({"id": command.id, "ok": result["ok"], "output": result["output"]})
        asked_ids = (
            {str(c.get("id")) for c in asked if isinstance(c, dict)}
            if isinstance(asked, list)
            else set()
        )
        for key in list(self.results):
            if key not in asked_ids and now - self.results[key].get("at", 0) > KEEP_SECONDS:
                del self.results[key]
                changed = True
        if changed:
            self._save()
        return reported

    def start(self, key: str, command: Command, reconciler: Any) -> None:
        """A backup or a restore, in the backups' thread."""
        from .backups import Job

        def done(ok: bool, output: str) -> None:
            self._finish(key, ok, output)

        compose_files, env_file = reconciler._files(command.slug)
        if not compose_files[0].exists() or not env_file.exists():
            self.results[key].update(
                ok=False, output=f"{command.slug} is not deployed on this host."
            )
            return
        if command.name == "backup":
            job = Job("backup", command.slug, reason="asked", done=done)
        else:
            job = Job(
                "restore",
                command.slug,
                backup_id=command.args["backup"],
                urls=command.args["urls"],
                done=done,
            )
        reconciler.backups.submit(job)

    def execute(self, command: Command, reconciler: Any) -> tuple[bool, str]:
        compose_files, env_file = reconciler._files(command.slug)
        if not compose_files[0].exists() or not env_file.exists():
            return False, f"{command.slug} is not deployed on this host."
        try:
            out = reconciler.docker.compose(
                command.slug, compose_files, env_file, command.compose_args(), timeout=TIMEOUT
            )
        except DockerError as error:
            return False, str(error)[-OUTPUT_CHARS:]
        logger.info("%s: command %s (%s) done", command.slug, command.id, command.name)
        return True, out[-OUTPUT_CHARS:]
