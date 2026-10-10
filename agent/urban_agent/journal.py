"""What happened on this host, kept on disk until the control plane has it.

Each event gets the next number of the journal. Reports carry the events the
control plane has not acknowledged yet (``events_ack`` in its answer), so those
recorded while it was unreachable reach it once it answers again. The journal
has an id of its own: a new one (state directory lost) starts again at 1, and
the control plane knows not to take those numbers for ones it already has.
"""

import json
import logging
import os
import secrets
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LEVELS = {"info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}
# Events kept while the control plane does not acknowledge them: the oldest go first.
LIMIT = 500
# Events sent in one report.
BATCH = 100
DETAIL_LIMIT = 12_000


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.id = ""
        self.seq = 0
        self.acked = 0
        self.events: list[dict[str, Any]] = []
        # Backups record events from their own thread.
        self.lock = threading.RLock()
        try:
            data = json.loads(path.read_text())
            self.id = str(data["id"])
            self.seq = int(data["seq"])
            self.acked = int(data["acked"])
            self.events = [e for e in data["events"] if isinstance(e, dict)]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if not self.id:
            self.id = secrets.token_hex(8)

    def record(self, level: str, message: str, slug: str = "", detail: str = "") -> None:
        logger.log(LEVELS.get(level, logging.INFO), "%s%s", f"{slug}: " if slug else "", message)
        with self.lock:
            self.seq += 1
            self.events.append(
                {
                    "seq": self.seq,
                    "at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "level": level,
                    "slug": slug,
                    "message": message[:500],
                    "detail": detail[-DETAIL_LIMIT:],
                }
            )
            del self.events[:-LIMIT]
            self.save()

    def pending(self) -> list[dict[str, Any]]:
        with self.lock:
            return [e for e in self.events if e["seq"] > self.acked][:BATCH]

    def acknowledge(self, answer: Any) -> None:
        """The control plane's answer to a report: ``{"events_ack": <last seq it has>}``."""
        ack = answer.get("events_ack") if isinstance(answer, dict) else None
        if not isinstance(ack, int) or isinstance(ack, bool) or ack <= self.acked:
            return
        with self.lock:
            self.acked = min(ack, self.seq)
            self.events = [e for e in self.events if e["seq"] > self.acked]
            self.save()

    def save(self) -> None:
        data = {"id": self.id, "seq": self.seq, "acked": self.acked, "events": self.events}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data))
            os.replace(temporary, self.path)
        except OSError as error:
            logger.warning("journal not saved: %s", error)
