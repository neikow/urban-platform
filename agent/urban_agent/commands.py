"""One-off commands the control plane asks for a website: its logs, a restart, its
setup again, the first administrator's invitation again.

Only these, with checked arguments: the control plane names a command, never what
runs. Each runs once (its id is remembered in ``commands.json``) and its result is
reported until the control plane stops asking, that is once it has the result.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .docker import DockerError

logger = logging.getLogger(__name__)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
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
        elif name in ("restart", "bootstrap", "invite_admin"):
            args = {}
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

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.results))

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
                ok, output = self.execute(command, reconciler)
                self.results[key] = {"ok": ok, "output": output, "at": now}
                changed = True
                if ok and command.name in DONE:
                    reconciler.journal.record("info", DONE[command.name], command.slug)
            result = self.results[key]
            reported.append({"id": command.id, "ok": result["ok"], "output": result["output"]})
        asked_ids = {str(r["id"]) for r in reported}
        for key in list(self.results):
            if key not in asked_ids and now - self.results[key].get("at", 0) > KEEP_SECONDS:
                del self.results[key]
                changed = True
        if changed:
            self._save()
        return reported

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
