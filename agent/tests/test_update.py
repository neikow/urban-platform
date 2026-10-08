import json

import pytest

from urban_agent import update
from urban_agent.config import Config
from urban_agent.docker import DockerError

AGENT = {
    "Name": "/urban-agent",
    "Image": "sha256:old",
    "Config": {
        "Env": [
            "CONTROL_PLANE_URL=https://cp.example.org",
            "AGENT_TOKEN=secret",
            "AGENT_VERSION=saas-aaaaaaa",
            "PATH=/usr/local/bin:/usr/bin",
        ]
    },
    "HostConfig": {"RestartPolicy": {"Name": "unless-stopped"}},
    "Mounts": [
        {
            "Type": "bind",
            "Source": "/var/run/docker.sock",
            "Destination": "/var/run/docker.sock",
            "RW": True,
        },
        {
            "Type": "volume",
            "Name": "urban-agent",
            "Destination": "/var/lib/urban-agent",
            "RW": True,
        },
    ],
    "NetworkSettings": {"Networks": {"nginx": {}, "monitoring": {}}},
}
IMAGE_ENV = ["PATH=/usr/local/bin:/usr/bin", "AGENT_VERSION=saas-aaaaaaa"]
NEW = "ghcr.io/neikow/urban-platform-agent:saas"


class FakeDocker:
    def __init__(self, new_version="saas-bbbbbbb"):
        self.calls = []
        self.new_version = new_version
        self.fail_on = None

    def pull(self, image):
        self.calls.append(("pull", image))

    def run(self, args, timeout=120):
        self.calls.append(tuple(args))
        if self.fail_on and tuple(args[: len(self.fail_on)]) == self.fail_on:
            raise DockerError("boom")
        if args[:2] == ["image", "inspect"]:
            image = args[-1]
            version = self.new_version if image == NEW else "saas-aaaaaaa"
            return json.dumps(["PATH=/usr/local/bin:/usr/bin", f"AGENT_VERSION={version}"])
        if args[:2] == ["container", "inspect"]:
            if args[-1] == update.HELPER_NAME:
                raise DockerError("no such container")
            return json.dumps([AGENT])
        return ""


@pytest.fixture
def updater(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "VERSION", "saas-aaaaaaa")
    monkeypatch.setenv("HOSTNAME", "abc123")
    config = Config(control_plane_url="https://cp.example.org", token="t", state_dir=tmp_path)
    return update.Updater(config, FakeDocker())


SPEC = {"image_tag": "saas", "version": "saas-bbbbbbb"}


class TestUpdater:
    def test_hands_over_to_a_helper_from_the_new_image(self, updater):
        assert updater.start(SPEC, now=1000)

        helper = updater.docker.calls[-1]
        assert helper[:5] == ("run", "-d", "--rm", "--name", update.HELPER_NAME)
        assert helper[-5:] == (NEW, "-m", "urban_agent.update", "abc123", NEW)
        assert ("pull", NEW) in updater.docker.calls

    @pytest.mark.parametrize(
        "spec",
        [None, {}, {"image_tag": "saas", "version": "saas-aaaaaaa"}, {"version": "x"}],
    )
    def test_nothing_to_do(self, updater, spec):
        assert not updater.start(spec, now=1000)
        assert updater.docker.calls == [] and updater.errors == []

    def test_only_its_own_image(self, updater):
        assert not updater.start({"image_tag": "x; rm -rf /", "version": "v"}, now=1000)
        assert updater.errors and updater.docker.calls == []

    def test_waits_for_the_version_to_be_published(self, updater):
        updater.docker.new_version = "saas-aaaaaaa"  # the tag not rebuilt yet

        assert not updater.start(SPEC, now=1000)
        assert "not saas-bbbbbbb yet" in updater.errors[0]
        assert not updater.start(SPEC, now=1000 + 60)  # not pulled again at once
        assert updater.docker.calls.count(("pull", NEW)) == 1
        updater.docker.new_version = "saas-bbbbbbb"
        assert updater.start(SPEC, now=1000 + update.RETRY_SECONDS)


class TestHelper:
    def test_same_settings_on_the_new_image(self):
        args = update.run_args(AGENT, IMAGE_ENV, NEW)

        assert args[:6] == ["run", "-d", "--name", "urban-agent", "--restart", "unless-stopped"]
        assert "/var/run/docker.sock:/var/run/docker.sock" in args
        assert "urban-agent:/var/lib/urban-agent" in args
        assert "AGENT_TOKEN=secret" in args and "CONTROL_PLANE_URL=https://cp.example.org" in args
        assert not any(a.startswith(("AGENT_VERSION=", "PATH=")) for a in args)
        assert args[args.index("--network") + 1] == "nginx"
        assert args[-1] == NEW
        assert update.extra_networks(AGENT) == ["monitoring"]

    def test_replace(self):
        docker = FakeDocker()

        assert update.replace("abc123", NEW, docker) == 0

        runs = [c for c in docker.calls if c[:2] == ("run", "-d")]
        assert ("rm", "-f", "abc123") in docker.calls
        assert runs[0][-1] == NEW
        assert ("network", "connect", "monitoring", "urban-agent") in docker.calls

    def test_back_to_the_old_image_if_the_new_one_fails(self):
        docker = FakeDocker()
        original = docker.run

        def new_one_fails(args, timeout=120):
            if args[:2] == ["run", "-d"] and args[-1] == NEW:
                docker.calls.append(tuple(args))
                raise DockerError("port already allocated")
            return original(args, timeout)

        docker.run = new_one_fails

        assert update.replace("abc123", NEW, docker) == 1
        runs = [c for c in docker.calls if c[:2] == ("run", "-d")]
        assert [r[-1] for r in runs] == [NEW, "sha256:old"]
