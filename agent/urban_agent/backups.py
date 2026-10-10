"""The websites' backups: their database and uploaded files, every day, kept on the host
and sent to an S3-compatible bucket.

The control plane turns them on for a host (``backup`` in the desired state): the hour
(UTC), how many to keep on the host, and the bucket. Each backup is a directory:

    backups/<slug>/<id>/db.dump         pg_dump, custom format (pg_restore)
    backups/<slug>/<id>/media.tar.gz    uploaded files, without the map tiles (rebuilt)
    backups/<slug>/<id>/manifest.json   the website's version, the files' sizes and hashes

``<id>`` is its UTC time, 20261010T030000Z. In the bucket: ``<prefix><slug>/<id>/…``,
the manifest last, once the files are there. The bucket's old backups are deleted by
the control plane, which also signs the links a restore downloads them from.

Backups and restores run one at a time in a thread of their own: the agent keeps
polling and reporting meanwhile, and leaves a website alone while one runs.
"""

import hashlib
import json
import logging
import queue
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .docker import DockerError
from .journal import Journal
from .s3 import Bucket, S3Error, put

logger = logging.getLogger(__name__)

ID = re.compile(r"^\d{8}T\d{6}Z$")
FILES = ("db.dump", "media.tar.gz")
MEDIA = "/app/mediafiles"
# A failed backup is tried again after this, at most a few times a day.
RETRY_SECONDS = 3600
DUMP_TIMEOUT = 3 * 3600
DOWNLOAD_TIMEOUT = 600
CHUNK = 1024 * 1024
# What runs while the database is restored.
APP_SERVICES = ["web", "worker", "nginx"]
# A restore goes into a new database, swapped in once complete.
RESTORED = "urban_restored"
PREVIOUS = "urban_previous"


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    hour: int = 3
    keep: int = 3
    bucket: Bucket | None = None

    @classmethod
    def parse(cls, data: Any) -> "Settings":
        if not isinstance(data, dict):
            raise BackupError("backup: not an object")
        hour, keep = data.get("hour", 3), data.get("keep", 3)
        if not isinstance(hour, int) or isinstance(hour, bool) or not 0 <= hour <= 23:
            raise BackupError(f"backup: invalid hour {hour!r}")
        if not isinstance(keep, int) or isinstance(keep, bool) or not 1 <= keep <= 30:
            raise BackupError(f"backup: invalid keep {keep!r}")
        bucket = None
        if data.get("s3") is not None:
            try:
                bucket = Bucket.parse(data["s3"])
            except S3Error as error:
                raise BackupError(f"backup: s3: {error}") from error
        return cls(hour=hour, keep=keep, bucket=bucket)


@dataclass
class Job:
    kind: str  # backup, restore
    slug: str
    reason: str = "scheduled"  # scheduled, asked, before a restore
    backup_id: str = ""
    urls: dict[str, str] = field(default_factory=dict)
    done: Callable[[bool, str], None] | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    if urlsplit(url).scheme != "https":
        raise BackupError("download links must be https")
    request = Request(url, headers={"User-Agent": "urban-agent"})
    try:
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response, target.open("wb") as out:  # nosec B310: https only
            shutil.copyfileobj(response, out, CHUNK)
    except OSError as error:
        raise BackupError(f"download of {target.name}: {error}") from error


class Backups:
    def __init__(self, root: Path, reconciler: Any, journal: Journal) -> None:
        self.root = root
        self.reconciler = reconciler
        self.journal = journal
        self.settings: Settings | None = None
        self.jobs: queue.Queue[Job] = queue.Queue()
        self.busy: set[str] = set()  # websites with a job queued or running
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None

    # --- Settings and schedule ---------------------------------------------------------

    def configure(self, data: Any, errors: list[str]) -> None:
        if data is None:
            self.settings = None
            return
        try:
            self.settings = Settings.parse(data)
        except BackupError as error:
            self.settings = None
            errors.append(str(error))

    def status_path(self, slug: str) -> Path:
        return self.root / slug / "status.json"

    def load_status(self, slug: str) -> dict[str, Any]:
        try:
            data = json.loads(self.status_path(slug).read_text())
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save_status(self, slug: str, status: dict[str, Any]) -> None:
        path = self.status_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(status))

    def due(self, slug: str, now: float) -> bool:
        """Its daily backup: not done since today's hour, not tried within the hour."""
        if self.settings is None or slug in self.busy:
            return False
        moment = datetime.fromtimestamp(now, UTC)
        scheduled = moment.replace(hour=self.settings.hour, minute=0, second=0, microsecond=0)
        if moment < scheduled:
            return False
        status = self.load_status(slug)
        if status.get("ok_at", 0) >= scheduled.timestamp():
            return False
        return now - status.get("tried_at", 0) >= RETRY_SECONDS

    def schedule(self, slugs: list[str], now: float) -> None:
        for slug in slugs:
            if self.due(slug, now):
                self.submit(Job("backup", slug))

    def submit(self, job: Job) -> None:
        with self.lock:
            self.busy.add(job.slug)
        self.jobs.put(job)
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._work, name="backups", daemon=True)
            self.thread.start()

    def is_busy(self, slug: str) -> bool:
        with self.lock:
            return slug in self.busy

    # --- The report --------------------------------------------------------------------

    def local(self, slug: str) -> list[dict[str, Any]]:
        """The backups on the host, newest first."""
        directory = self.root / slug
        found = []
        for path in sorted(directory.iterdir() if directory.is_dir() else [], reverse=True):
            manifest = path / "manifest.json"
            if not ID.match(path.name) or not manifest.exists():
                continue
            try:
                data = json.loads(manifest.read_text())
            except (OSError, ValueError):
                continue
            files = data.get("files", {})
            found.append(
                {
                    "id": path.name,
                    "size": sum(f.get("size", 0) for f in files.values()),
                    "version": data.get("version", ""),
                    "uploaded": bool(data.get("uploaded")),
                }
            )
        return found

    def report(self, slug: str) -> dict[str, Any]:
        status = self.load_status(slug)
        last = status.get("last")
        if not last and not self.is_busy(slug) and not (self.root / slug).is_dir():
            return {}
        return {"running": self.is_busy(slug), "last": last or {}, "local": self.local(slug)}

    # --- The work, in its own thread ----------------------------------------------------

    def _work(self) -> None:
        while True:
            try:
                job = self.jobs.get(timeout=5)
            except queue.Empty:
                return  # started again by the next submit
            try:
                if job.kind == "backup":
                    ok, output = self._backup(job)
                else:
                    ok, output = self._restore(job)
            except Exception as error:  # a bug must not kill the thread for good
                logger.exception("%s: %s failed", job.slug, job.kind)
                ok, output = False, f"{job.kind}: {error}"
            with self.lock:
                if not any(j.slug == job.slug for j in list(self.jobs.queue)):
                    self.busy.discard(job.slug)
            if job.done:
                job.done(ok, output)

    def _compose(self, slug: str) -> tuple[list[Path], Path]:
        compose_files, env_file = self.reconciler._files(slug)
        if not compose_files[0].exists() or not env_file.exists():
            raise BackupError(f"{slug} is not deployed on this host.")
        return compose_files, env_file

    def _backup(self, job: Job) -> tuple[bool, str]:
        slug = job.slug
        now = time.time()
        backup_id = self._new_id(slug, now)
        status = self.load_status(slug)
        status["tried_at"] = now
        self.save_status(slug, status)
        started = time.monotonic()
        try:
            path = self._make(slug, backup_id)
        except (BackupError, DockerError, OSError) as error:
            status["last"] = {"id": backup_id, "ok": False, "error": str(error)[-1000:], "at": now}
            self.save_status(slug, status)
            self.journal.record("error", f"Backup failed: {error}"[:500], slug, detail=str(error))
            return False, str(error)
        manifest = json.loads((path / "manifest.json").read_text())
        size = sum(f["size"] for f in manifest["files"].values())
        upload_error = ""
        settings = self.settings
        if settings and settings.bucket:
            try:
                self._upload(settings.bucket, slug, path, manifest)
            except (S3Error, OSError) as error:
                upload_error = str(error)
        self._prune(slug)
        seconds = time.monotonic() - started
        status["last"] = {
            "id": backup_id,
            "ok": not upload_error,
            "error": upload_error[-1000:],
            "at": now,
            "size": size,
            "uploaded": bool(settings and settings.bucket and not upload_error),
        }
        if not upload_error:
            status["ok_at"] = now
        self.save_status(slug, status)
        megabytes = size / 1024 / 1024
        if upload_error:
            message = f"Backup {backup_id} kept on the host only: its upload failed."
            self.journal.record("error", message, slug, detail=upload_error)
            return False, f"{message}\n{upload_error}"
        where = " and sent to the bucket" if settings and settings.bucket else ""
        message = f"Backup {backup_id} ({megabytes:.0f} MB) made in {seconds:.0f} s{where}."
        if job.reason != "scheduled":
            message += f" ({job.reason})"
        self.journal.record("info", message, slug)
        return True, message

    def _new_id(self, slug: str, now: float) -> str:
        """Its UTC time; the next free second if one was made this second (before a
        restore of the one just made)."""
        moment = int(now)
        while True:
            backup_id = datetime.fromtimestamp(moment, UTC).strftime("%Y%m%dT%H%M%SZ")
            if not (self.root / slug / backup_id).exists():
                return backup_id
            moment += 1

    def _make(self, slug: str, backup_id: str) -> Path:
        compose_files, env_file = self._compose(slug)
        directory = self.root / slug
        partial = directory / f".{backup_id}.partial"
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir(parents=True)
        try:
            docker = self.reconciler.docker
            docker.compose_stream(
                slug,
                compose_files,
                env_file,
                ["exec", "-T", "db", "pg_dump", "-U", "urban", "-d", "urban", "-Fc"],
                stdout=partial / "db.dump",
                timeout=DUMP_TIMEOUT,
            )
            docker.compose_stream(
                slug,
                compose_files,
                env_file,
                [
                    "exec",
                    "-T",
                    "web",
                    "tar",
                    "-czf",
                    "-",
                    "-C",
                    MEDIA,
                    "--exclude=./map-tiles",
                    ".",
                ],
                stdout=partial / "media.tar.gz",
                timeout=DUMP_TIMEOUT,
            )
            status = self.reconciler.load_status(slug)
            manifest = {
                "id": backup_id,
                "slug": slug,
                "version": status.version,
                "files": {
                    name: {
                        "size": (partial / name).stat().st_size,
                        "sha256": sha256(partial / name),
                    }
                    for name in FILES
                },
                "uploaded": False,
            }
            (partial / "manifest.json").write_text(json.dumps(manifest, indent=2))
            target = directory / backup_id
            partial.rename(target)
            return target
        except BaseException:
            shutil.rmtree(partial, ignore_errors=True)
            raise

    def _upload(self, bucket: Bucket, slug: str, path: Path, manifest: dict[str, Any]) -> None:
        key = f"{bucket.prefix}{slug}/{path.name}/"
        for name in FILES:
            put(bucket, key + name, path / name, manifest["files"][name]["sha256"])
        # The manifest last: a backup with its manifest in the bucket is complete.
        manifest["uploaded"] = True
        text = json.dumps(manifest, indent=2)
        (path / "manifest.json").write_text(text)
        put(
            bucket,
            key + "manifest.json",
            path / "manifest.json",
            hashlib.sha256(text.encode()).hexdigest(),
        )

    def _prune(self, slug: str) -> None:
        keep = self.settings.keep if self.settings else 3
        for old in self.local(slug)[keep:]:
            shutil.rmtree(self.root / slug / old["id"], ignore_errors=True)

    def _restore_database(
        self, slug: str, compose_files: list[Path], env_file: Path, dump: Path
    ) -> None:
        """Into a new database, then swapped in: tables the backup does not have (from a
        newer release) do not linger, and a failed restore leaves the current one."""
        docker = self.reconciler.docker

        def psql(*statements: str) -> None:
            args = [
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "urban",
                "-d",
                "postgres",
                "-v",
                "ON_ERROR_STOP=1",
            ]
            for statement in statements:
                args += ["-c", statement]
            docker.compose(slug, compose_files, env_file, args, timeout=300)

        psql(f"DROP DATABASE IF EXISTS {RESTORED}", f"CREATE DATABASE {RESTORED} OWNER urban")
        try:
            docker.compose_stream(
                slug,
                compose_files,
                env_file,
                [
                    "exec",
                    "-T",
                    "db",
                    "pg_restore",
                    "-U",
                    "urban",
                    "-d",
                    RESTORED,
                    "--no-owner",
                    "--exit-on-error",
                ],
                stdin=dump,
                timeout=DUMP_TIMEOUT,
            )
        except DockerError:
            psql(f"DROP DATABASE IF EXISTS {RESTORED}")
            raise
        psql(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = 'urban' AND pid <> pg_backend_pid()",
            f"DROP DATABASE IF EXISTS {PREVIOUS}",
            f"ALTER DATABASE urban RENAME TO {PREVIOUS}",
            f"ALTER DATABASE {RESTORED} RENAME TO urban",
            # Its data is in the backup made before the restore.
            f"DROP DATABASE {PREVIOUS}",
        )

    def _restore(self, job: Job) -> tuple[bool, str]:
        slug, backup_id = job.slug, job.backup_id
        directory = self.root / slug / backup_id
        downloaded = False
        try:
            compose_files, env_file = self._compose(slug)
            if not (directory / "manifest.json").exists():
                if not job.urls:
                    raise BackupError(f"Backup {backup_id} is not on the host, and no link to it.")
                directory = self.root / slug / f".{backup_id}.download"
                shutil.rmtree(directory, ignore_errors=True)
                directory.mkdir(parents=True)
                downloaded = True
                for name in FILES:
                    download(job.urls[name], directory / name)
            # First, what there is now: a restore can be undone.
            ok, output = self._backup(Job("backup", slug, reason="before a restore"))
            if not ok and "kept on the host only" not in output:
                raise BackupError(f"No backup of the current data could be made: {output}")
            docker = self.reconciler.docker
            docker.compose(slug, compose_files, env_file, ["stop", *APP_SERVICES], timeout=300)
            try:
                self._restore_database(slug, compose_files, env_file, directory / "db.dump")
                docker.compose_stream(
                    slug,
                    compose_files,
                    env_file,
                    [
                        "run",
                        "--rm",
                        "--no-deps",
                        "-T",
                        "--entrypoint",
                        "sh",
                        "web",
                        "-c",
                        f"find {MEDIA} -mindepth 1 -maxdepth 1 ! -name map-tiles "
                        f"-exec rm -rf {{}} + && tar -xzf - -C {MEDIA}",
                    ],
                    stdin=directory / "media.tar.gz",
                    timeout=DUMP_TIMEOUT,
                )
            finally:
                # Back up, with migrations if the backup is from an older release.
                docker.compose(
                    slug, compose_files, env_file, ["up", "--detach", "--wait"], timeout=1200
                )
        except (BackupError, DockerError, OSError) as error:
            self.journal.record(
                "error", f"Restore of {backup_id} failed: {error}"[:500], slug, detail=str(error)
            )
            return False, str(error)
        finally:
            if downloaded:
                shutil.rmtree(directory, ignore_errors=True)
        message = f"Restored backup {backup_id}."
        self.journal.record("warning", message, slug)
        return True, message
