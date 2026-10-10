import json
import time
from datetime import UTC, datetime

import pytest

from urban_agent import backups as backups_module
from urban_agent.backups import BackupError, Job, Settings
from urban_agent.s3 import Bucket, S3Error, sign

from .test_reconcile import FakeDocker, desired, tenant
from urban_agent.config import Config
from urban_agent.reconcile import Reconciler

S3 = {
    "endpoint": "https://s3.example.org",
    "region": "fr-par",
    "bucket": "backups",
    "access_key": "AK",
    "secret_key": "SK",
    "prefix": "urban",
}
# 2026-10-10 04:00 UTC: after a 03:00 schedule.
NOW = datetime(2026, 10, 10, 4, 0, tzinfo=UTC).timestamp()


@pytest.fixture
def docker():
    return FakeDocker()


@pytest.fixture
def agent(tmp_path, docker):
    config = Config(control_plane_url="https://cp.example.org", token="t", state_dir=tmp_path)
    reconciler = Reconciler(config, docker)
    reconciler.reconcile(desired(tenant()), now=NOW - 7200)  # deployed
    return reconciler


@pytest.fixture
def uploads(monkeypatch):
    sent = []
    monkeypatch.setattr(
        backups_module, "put", lambda bucket, key, path, digest: sent.append((key, path.name))
    )
    return sent


class TestSettings:
    def test_defaults(self):
        settings = Settings.parse({})

        assert (settings.hour, settings.keep, settings.bucket) == (3, 3, None)

    def test_bucket(self):
        settings = Settings.parse({"hour": 2, "keep": 5, "s3": S3})

        assert settings.bucket.prefix == "urban/" and settings.bucket.host == "s3.example.org"

    @pytest.mark.parametrize(
        "data",
        [
            {"hour": 24},
            {"keep": 0},
            {"s3": {**S3, "endpoint": "http://s3.example.org"}},
            {"s3": {**S3, "secret_key": ""}},
            {"s3": {**S3, "prefix": "../other"}},
        ],
    )
    def test_refused(self, data):
        with pytest.raises(BackupError):
            Settings.parse(data)


def test_signature_matches_aws_example():
    """The GET object example of AWS's Signature Version 4 documentation."""
    headers = {
        "host": "examplebucket.s3.amazonaws.com",
        "range": "bytes=0-9",
        "x-amz-content-sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "x-amz-date": "20130524T000000Z",
    }

    authorization = sign(
        "GET",
        "/test.txt",
        headers,
        headers["x-amz-content-sha256"],
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        now=datetime(2013, 5, 24, tzinfo=UTC),
    )

    assert authorization.endswith(
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    )


def test_bucket_paths():
    bucket = Bucket.parse(S3)

    assert bucket.path("urban/aix/20261010T030000Z/db.dump") == (
        "/backups/urban/aix/20261010T030000Z/db.dump"
    )
    with pytest.raises(S3Error):
        Bucket.parse({**S3, "endpoint": "https://s3.example.org/path"})


class TestBackup:
    def test_made_kept_and_uploaded(self, agent, docker, uploads, tmp_path):
        agent.backups.configure({"s3": S3}, [])

        ok, output = agent.backups._backup(Job("backup", "aix"))

        assert ok, output
        [backup] = agent.backups.local("aix")
        directory = tmp_path / "backups" / "aix" / backup["id"]
        assert (directory / "db.dump").read_bytes() == b"db data"
        manifest = json.loads((directory / "manifest.json").read_text())
        assert manifest["version"] == "1.4.0" and manifest["uploaded"]
        assert set(manifest["files"]) == {"db.dump", "media.tar.gz"}
        assert [name for _, name in uploads] == ["db.dump", "media.tar.gz", "manifest.json"]
        assert uploads[0][0] == f"urban/aix/{backup['id']}/db.dump"
        assert docker.calls[-2][:8] == (
            "stream",
            "aix",
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            "urban",
        )

    def test_upload_failure_keeps_it_on_the_host(self, agent, monkeypatch):
        def fail(*args):
            raise S3Error("upload of x: HTTP 403 AccessDenied")

        monkeypatch.setattr(backups_module, "put", fail)
        agent.backups.configure({"s3": S3}, [])

        ok, output = agent.backups._backup(Job("backup", "aix"))

        assert not ok and "kept on the host only" in output
        report = agent.backups.report("aix")
        assert report["last"]["error"] == "upload of x: HTTP 403 AccessDenied"
        assert report["local"][0]["uploaded"] is False

    def test_failure_cleans_up(self, agent, docker, tmp_path):
        agent.backups.configure({}, [])
        docker.fail = ("stream", "aix", "exec", "-T", "web")

        ok, _ = agent.backups._backup(Job("backup", "aix"))

        assert not ok
        assert agent.backups.local("aix") == []
        assert not list((tmp_path / "backups" / "aix").glob(".*partial"))
        assert agent.backups.report("aix")["last"]["ok"] is False

    def test_only_the_latest_kept(self, agent, monkeypatch):
        agent.backups.configure({"keep": 2}, [])
        moments = iter([NOW, NOW + 10, NOW + 20])
        monkeypatch.setattr(backups_module.time, "time", lambda: next(moments))

        for _ in range(3):
            agent.backups._backup(Job("backup", "aix"))

        assert [b["id"] for b in agent.backups.local("aix")] == [
            "20261010T040020Z",
            "20261010T040010Z",
        ]


class TestSchedule:
    def test_due_once_a_day_after_its_hour(self, agent):
        agent.backups.configure({"hour": 3}, [])

        assert not agent.backups.due("aix", NOW - 2 * 3600)  # 02:00: not yet
        assert agent.backups.due("aix", NOW)
        agent.backups.save_status("aix", {"ok_at": NOW, "tried_at": NOW})
        assert not agent.backups.due("aix", NOW + 3600)
        assert agent.backups.due("aix", NOW + 24 * 3600)

    def test_failure_tried_again_an_hour_later(self, agent):
        agent.backups.configure({}, [])
        agent.backups.save_status("aix", {"tried_at": NOW})

        assert not agent.backups.due("aix", NOW + 600)
        assert agent.backups.due("aix", NOW + 3600)

    def test_off_without_settings(self, agent):
        assert not agent.backups.due("aix", NOW)

    def test_invalid_settings_reported(self, agent):
        report = agent.reconcile({**desired(tenant()), "backup": {"hour": 99}}, now=NOW)

        assert "backup: invalid hour 99" in report["errors"]


def wait_idle(agent, seconds=5.0):
    deadline = time.monotonic() + seconds
    while agent.backups.is_busy("aix") and time.monotonic() < deadline:
        time.sleep(0.02)


class TestThroughThePoll:
    def test_scheduled_in_the_background(self, agent, uploads):
        report = agent.reconcile({**desired(tenant()), "backup": {"s3": S3}}, now=NOW)
        wait_idle(agent)

        report = agent.reconcile({**desired(tenant()), "backup": {"s3": S3}}, now=NOW + 30)
        backups = report["tenants"][0]["backups"]
        assert backups["running"] is False and backups["last"]["ok"]
        assert len(backups["local"]) == 1

    def test_asked_then_reported(self, agent, uploads):
        ask = {**desired(tenant()), "commands": [{"id": 3, "slug": "aix", "name": "backup"}]}

        agent.reconcile(ask, now=NOW - 3600)
        wait_idle(agent)
        report = agent.reconcile(ask, now=NOW - 3570)

        [result] = report["commands"]
        assert result["id"] == 3 and result["ok"] and "made in" in result["output"]

    def test_website_left_alone_while_busy(self, agent, docker):
        agent.backups.busy.add("aix")
        docker.calls.clear()

        agent.reconcile(desired(tenant(generation=2, image_tag="1.5.0")), now=NOW)

        assert not docker.composed("aix", "up")

    def test_purge_deletes_its_backups(self, agent, tmp_path):
        agent.backups.configure({}, [])
        agent.backups._backup(Job("backup", "aix"))

        agent.reconcile(
            desired({"slug": "aix", "generation": 9, "state": "absent", "purge": True}), now=NOW
        )

        assert not (tmp_path / "backups" / "aix").exists()


class TestRestore:
    def test_from_the_host(self, agent, docker):
        agent.backups.configure({}, [])
        agent.backups._backup(Job("backup", "aix"))
        [backup] = agent.backups.local("aix")
        docker.calls.clear()

        ok, output = agent.backups._restore(Job("restore", "aix", backup_id=backup["id"]))

        assert ok, output
        streams = [c for c in docker.calls if c[0] == "stream"]
        # A backup of the current data first, then the database and the files.
        assert [c[5] if c[4] == "db" else c[4] for c in streams[:2]] == ["pg_dump", "web"]
        # Into a new database, swapped in once complete.
        assert "pg_restore" in streams[2] and "urban_restored" in streams[2]
        swap = docker.composed("aix", "exec", "-T", "db", "psql")[-1]
        assert "ALTER DATABASE urban_restored RENAME TO urban" in swap
        assert streams[3][2] == "run"
        assert docker.composed("aix", "stop", "web", "worker", "nginx")
        assert docker.composed("aix", "up", "--detach", "--wait")
        assert len(agent.backups.local("aix")) == 2

    def test_downloaded(self, agent, docker, monkeypatch):
        fetched = []

        def fake_download(url, target):
            fetched.append(url)
            target.write_bytes(b"x")

        monkeypatch.setattr(backups_module, "download", fake_download)
        agent.backups.configure({}, [])
        urls = {"db.dump": "https://s3/db", "media.tar.gz": "https://s3/media"}

        ok, _ = agent.backups._restore(
            Job("restore", "aix", backup_id="20260101T030000Z", urls=urls)
        )

        assert ok and fetched == ["https://s3/db", "https://s3/media"]

    def test_unknown_backup(self, agent):
        ok, output = agent.backups._restore(Job("restore", "aix", backup_id="20260101T030000Z"))

        assert not ok and "not on the host" in output

    def test_app_started_again_after_a_failure(self, agent, docker):
        agent.backups.configure({}, [])
        agent.backups._backup(Job("backup", "aix"))
        [backup] = agent.backups.local("aix")
        docker.fail = ("stream", "aix", "exec", "-T", "db", "pg_restore")

        ok, _ = agent.backups._restore(Job("restore", "aix", backup_id=backup["id"]))

        assert not ok
        assert docker.composed("aix", "up", "--detach", "--wait")
        # The new database dropped, the current one never renamed.
        statements = [
            c for call in docker.composed("aix", "exec", "-T", "db", "psql") for c in call
        ]
        assert "DROP DATABASE IF EXISTS urban_restored" in statements
        assert "ALTER DATABASE urban RENAME TO urban_previous" not in statements

    @pytest.mark.parametrize(
        "args",
        [
            {"backup": "yesterday"},
            {
                "backup": "20260101T030000Z",
                "urls": {"db.dump": "http://s3/db", "media.tar.gz": "https://s3/m"},
            },
            {"backup": "20260101T030000Z", "urls": {"db.dump": "https://s3/db"}},
        ],
    )
    def test_refused(self, agent, args):
        report = agent.reconcile(
            {
                **desired(tenant()),
                "commands": [{"id": 4, "slug": "aix", "name": "restore", "args": args}],
            },
            now=NOW,
        )

        assert report["commands"] == [] and report["errors"]
