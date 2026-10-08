import json
import stat
from pathlib import Path

import pytest

from urban_agent.config import Config
from urban_agent.docker import DockerError
from urban_agent.reconcile import (
    COMPOSE_PATH_IN_IMAGE,
    InvalidTenant,
    Reconciler,
    Tenant,
    env_file_content,
)

IMAGE = "ghcr.io/neikow/urban-platform"


class FakeDocker:
    """Records the commands; ``fail`` makes those starting with it raise."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail: tuple[str, ...] | None = None
        self.version = "1.4.0"
        self.stats = '{"pages": 12, "users": 40}'

    def _call(self, *call: str) -> None:
        self.calls.append(call)
        if self.fail and call[: len(self.fail)] == self.fail:
            raise DockerError(f"boom: {' '.join(call)}")

    def pull(self, image: str) -> None:
        self._call("pull", image)

    def read_file(self, image: str, path: str) -> str:
        self._call("read_file", image, path)
        return "services: {}\n"

    def ensure_network(self, name: str) -> None:
        self._call("network", name)

    def compose(self, project, compose_file, env_file, args, timeout=120) -> str:
        self._call("compose", project, *args)
        if args[0] != "exec":
            return ""
        return self.stats if "tenant_stats" in args else self.version

    def compose_services(self, project, compose_file, env_file):
        self._call("ps", project)
        return [{"Service": "web", "State": "running", "Health": "healthy"}]

    def composed(self, *args: str) -> list[tuple[str, ...]]:
        return [c for c in self.calls if c[: 1 + len(args)] == ("compose", *args)]


@pytest.fixture
def docker():
    return FakeDocker()


@pytest.fixture
def agent(tmp_path, docker):
    config = Config(control_plane_url="https://cp.example.org", token="t", state_dir=tmp_path)
    return Reconciler(config, docker)


def tenant(**changes):
    data = {
        "slug": "aix",
        "generation": 1,
        "state": "running",
        "image_tag": "1.4.0",
        "env": {"TENANT_HOSTNAME": "aix.example.org", "SECRET_KEY": "a$b"},
    }
    return {**data, **changes}


def desired(*tenants, edge=None):
    return {"edge": edge or {"acme_email": "ops@example.org"}, "tenants": list(tenants)}


class TestValidation:
    @pytest.mark.parametrize(
        "changes",
        [
            {"slug": "Aix"},
            {"slug": "../etc"},
            {"slug": "a" * 41},
            {"state": "deleted"},
            {"generation": "1"},
            {"image_tag": "1.4.0; rm -rf /"},
            {"env": {"lower": "x"}},
            {"env": {"IMAGE": "evil/image"}},
            {"env": {"TENANT_SLUG": "other"}},
            {"env": {"KEY": "it's"}},
            {"env": {"KEY": "two\nlines"}},
            {"env": {"KEY": 3}},
        ],
    )
    def test_rejects(self, changes):
        with pytest.raises(InvalidTenant):
            Tenant.parse(tenant(**changes))

    def test_absent_needs_no_release(self):
        parsed = Tenant.parse({"slug": "aix", "generation": 2, "state": "absent", "purge": True})

        assert parsed.purge

    def test_env_file_is_literal_and_pins_the_image(self):
        content = env_file_content(Tenant.parse(tenant()), IMAGE)

        assert "SECRET_KEY='a$b'\n" in content
        assert f"IMAGE='{IMAGE}'\n" in content
        assert "IMAGE_TAG='1.4.0'\n" in content
        assert "TENANT_SLUG='aix'\n" in content


class TestDeploy:
    def test_first_deployment(self, agent, docker, tmp_path):
        report = agent.reconcile(desired(tenant()), now=1000)

        assert ("pull", f"{IMAGE}:1.4.0") in docker.calls
        assert ("pull", f"{IMAGE}-nginx:1.4.0") in docker.calls
        assert ("read_file", f"{IMAGE}:1.4.0", COMPOSE_PATH_IN_IMAGE) in docker.calls
        assert docker.composed("aix", "up")
        env_file = tmp_path / "tenants" / "aix" / ".env"
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
        [status] = report["tenants"]
        assert status["status"] == "running"
        assert status["generation"] == 1
        assert status["version"] == "1.4.0"
        assert status["services"] == {"web": "healthy"}
        assert report["edge"] == "running"

    def test_nothing_to_do_at_the_next_poll(self, agent, docker):
        agent.reconcile(desired(tenant()), now=1000)
        docker.calls.clear()

        agent.reconcile(desired(tenant()), now=1030)

        assert not docker.composed("aix", "up")
        assert not [c for c in docker.calls if c[0] == "pull"]

    def test_new_generation_redeploys(self, agent, docker):
        agent.reconcile(desired(tenant()), now=1000)
        docker.calls.clear()

        agent.reconcile(desired(tenant(generation=2, image_tag="1.5.0")), now=1030)

        assert ("pull", f"{IMAGE}:1.5.0") in docker.calls
        assert docker.composed("aix", "up")

    def test_failure_is_reported_then_retried_later(self, agent, docker):
        docker.fail = ("compose", "aix", "up")

        report = agent.reconcile(desired(tenant()), now=1000)

        [status] = report["tenants"]
        assert status["status"] == "failed"
        assert "boom" in status["error"]
        assert status["generation"] is None

        docker.calls.clear()
        agent.reconcile(desired(tenant()), now=1030)
        assert not docker.composed("aix", "up")  # not at every poll

        docker.fail = None
        report = agent.reconcile(desired(tenant()), now=1000 + 301)
        assert report["tenants"][0]["status"] == "running"

    def test_a_new_generation_is_tried_at_once_after_a_failure(self, agent, docker):
        docker.fail = ("compose", "aix", "up")
        agent.reconcile(desired(tenant()), now=1000)
        docker.fail = None

        report = agent.reconcile(desired(tenant(generation=2)), now=1001)

        assert report["tenants"][0]["status"] == "running"

    def test_one_failing_website_does_not_block_the_others(self, agent, docker):
        docker.fail = ("compose", "aix", "up")

        report = agent.reconcile(desired(tenant(), tenant(slug="arles")), now=1000)

        statuses = {t["slug"]: t["status"] for t in report["tenants"]}
        assert statuses == {"aix": "failed", "arles": "running"}

    def test_invalid_website_is_reported_not_applied(self, agent, docker):
        report = agent.reconcile(desired(tenant(slug="../x")), now=1000)

        assert report["errors"] and report["tenants"] == []
        assert not [c for c in docker.calls if c[0] in ("pull", "read_file")]


class TestLifecycle:
    def test_stop_then_start_again(self, agent, docker):
        agent.reconcile(desired(tenant()), now=1000)

        report = agent.reconcile(desired(tenant(generation=2, state="stopped")), now=1030)
        assert docker.composed("aix", "stop")
        assert report["tenants"][0]["status"] == "stopped"

        docker.calls.clear()
        report = agent.reconcile(desired(tenant(generation=3)), now=1060)
        assert docker.composed("aix", "up")
        assert report["tenants"][0]["status"] == "running"

    def test_absent_keeps_the_data_unless_purged(self, agent, docker, tmp_path):
        agent.reconcile(desired(tenant()), now=1000)

        agent.reconcile(desired({"slug": "aix", "generation": 2, "state": "absent"}), now=1030)

        [down] = docker.composed("aix", "down")
        assert "--volumes" not in down
        assert not (tmp_path / "tenants" / "aix").exists()

    def test_purge_deletes_the_data(self, agent, docker):
        agent.reconcile(desired(tenant()), now=1000)

        agent.reconcile(
            desired({"slug": "aix", "generation": 2, "state": "absent", "purge": True}), now=1030
        )

        [down] = docker.composed("aix", "down")
        assert "--volumes" in down

    def test_websites_left_out_are_left_alone(self, agent, docker):
        agent.reconcile(desired(tenant()), now=1000)
        docker.calls.clear()

        report = agent.reconcile(desired(), now=1030)

        assert not docker.composed("aix", "stop") and not docker.composed("aix", "down")
        [status] = report["tenants"]
        assert status["slug"] == "aix" and status["status"] == "running"


class TestEdge:
    def test_started_once(self, agent, docker, tmp_path):
        agent.reconcile(desired(), now=1000)
        agent.reconcile(desired(), now=1030)

        assert len(docker.composed("urban-edge", "up")) == 1
        assert "ACME_EMAIL='ops@example.org'" in (tmp_path / "edge.env").read_text()

    def test_restarted_when_the_email_changes(self, agent, docker):
        agent.reconcile(desired(), now=1000)
        agent.reconcile(desired(edge={"acme_email": "new@example.org"}), now=1030)

        assert len(docker.composed("urban-edge", "up")) == 2

    def test_failure_is_reported(self, agent, docker):
        docker.fail = ("compose", "urban-edge")

        report = agent.reconcile(desired(), now=1000)

        assert report["edge"].startswith("failed")


def test_state_survives_a_restart(tmp_path, docker):
    config = Config(control_plane_url="https://cp.example.org", token="t", state_dir=tmp_path)
    Reconciler(config, docker).reconcile(desired(tenant()), now=1000)
    docker.calls.clear()

    Reconciler(config, docker).reconcile(desired(tenant()), now=1030)

    assert not docker.composed("aix", "up")
    state = json.loads(Path(tmp_path / "tenants" / "aix" / "state.json").read_text())
    assert state["generation"] == 1


class TestDockerPull:
    def test_falls_back_to_the_local_image(self, monkeypatch):
        from urban_agent.docker import Docker

        calls = []

        def run(self, args, timeout=120):
            calls.append(args[0])
            if args[0] == "pull":
                raise DockerError("registry down")
            return "sha256:abc"

        monkeypatch.setattr(Docker, "run", run)

        Docker().pull(f"{IMAGE}:1.4.0")

        assert calls == ["pull", "image"]

    def test_fails_without_a_local_copy(self, monkeypatch):
        from urban_agent.docker import Docker

        def run(self, args, timeout=120):
            raise DockerError("registry down" if args[0] == "pull" else "no such image")

        monkeypatch.setattr(Docker, "run", run)

        with pytest.raises(DockerError, match="registry down"):
            Docker().pull(f"{IMAGE}:1.4.0")


class TestExternalEdge:
    """The host's own reverse proxy, with its own certificates."""

    EXTERNAL = {"mode": "external"}

    def test_websites_get_a_local_port(self, agent, docker, tmp_path):
        report = agent.reconcile(desired(tenant(http_port=8101), edge=self.EXTERNAL), now=1000)

        assert report["edge"] == "external"
        assert report["tenants"][0]["status"] == "running"
        override = (tmp_path / "tenants" / "aix" / "compose.override.yml").read_text()
        assert '"127.0.0.1:8101:80"' in override
        # Our Traefik is stopped, never started: ports 80/443 are the proxy's.
        assert docker.composed("urban-edge", "down")
        assert not docker.composed("urban-edge", "up")

    def test_port_required(self, agent, docker):
        report = agent.reconcile(desired(tenant(), edge=self.EXTERNAL), now=1000)

        assert report["tenants"] == []
        assert "http_port required" in report["errors"][0]

    def test_ports_are_unique(self, agent):
        report = agent.reconcile(
            desired(
                tenant(http_port=8101), tenant(slug="arles", http_port=8101), edge=self.EXTERNAL
            ),
            now=1000,
        )

        assert [t["slug"] for t in report["tenants"]] == ["aix"]
        assert "already used by aix" in report["errors"][0]

    @pytest.mark.parametrize("port", [80, 70000, "8101", True])
    def test_invalid_port(self, port):
        with pytest.raises(InvalidTenant):
            Tenant.parse(tenant(http_port=port))

    def test_back_to_traefik_drops_the_port(self, agent, tmp_path):
        agent.reconcile(desired(tenant(http_port=8101), edge=self.EXTERNAL), now=1000)

        agent.reconcile(desired(tenant(generation=2, http_port=8101)), now=1030)

        assert not (tmp_path / "tenants" / "aix" / "compose.override.yml").exists()

    def test_traefik_needs_an_email(self, agent, docker):
        report = agent.reconcile(desired(edge={"mode": "traefik"}), now=1000)

        assert report["edge"] == "acme_email required"
        assert not docker.composed("urban-edge", "up")


class TestProxyNetwork:
    """A host proxy running in Docker: websites join its network instead of a port."""

    EDGE = {"mode": "external", "network": "nginx"}

    def test_websites_join_the_proxy_network(self, agent, docker, tmp_path):
        report = agent.reconcile(desired(tenant(), edge=self.EDGE), now=1000)

        assert report["errors"] == []
        assert report["tenants"][0]["status"] == "running"
        override = (tmp_path / "tenants" / "aix" / "compose.override.yml").read_text()
        assert 'aliases: ["aix-nginx"]' in override
        assert "name: nginx\n    external: true" in override
        assert "127.0.0.1" not in override
        assert not docker.composed("urban-edge", "up")

    def test_port_ignored(self, agent, tmp_path):
        agent.reconcile(desired(tenant(http_port=8101), edge=self.EDGE), now=1000)

        override = (tmp_path / "tenants" / "aix" / "compose.override.yml").read_text()
        assert "8101" not in override

    def test_invalid_network(self, agent):
        report = agent.reconcile(
            desired(tenant(), edge={"mode": "external", "network": "bad name;"}), now=1000
        )

        assert "invalid proxy network" in report["errors"][0]
        # Without a usable network, the websites need a port.
        assert "http_port required" in report["errors"][1]


class TestStats:
    def stats_calls(self, docker):
        return [c for c in docker.composed("aix", "exec") if "tenant_stats" in c]

    def test_collected_after_a_deployment_then_every_interval(self, agent, docker):
        report = agent.reconcile(desired(tenant()), now=1000)
        assert report["tenants"][0]["stats"] == {"pages": 12, "users": 40}
        assert "stats_at" not in report["tenants"][0]

        docker.stats = '{"pages": 13, "users": 41}'
        report = agent.reconcile(desired(tenant()), now=1000 + 60)
        assert report["tenants"][0]["stats"] == {"pages": 12, "users": 40}  # not yet
        report = agent.reconcile(desired(tenant()), now=1000 + 900)
        assert report["tenants"][0]["stats"] == {"pages": 13, "users": 41}
        assert len(self.stats_calls(docker)) == 2

    def test_an_old_release_without_the_command(self, agent, docker):
        docker.fail = ("compose", "aix", "exec", "-T", "web", "python", "manage.py")

        report = agent.reconcile(desired(tenant()), now=1000)
        agent.reconcile(desired(tenant()), now=1060)

        assert report["tenants"][0]["status"] == "running"
        assert report["tenants"][0]["stats"] == {}
        assert len(self.stats_calls(docker)) == 1  # not retried at every poll

    def test_only_counts_are_kept(self, agent, docker):
        docker.stats = 'Some warning\n{"pages": 3, "users": -1, "name": "x", "flag": true}'

        report = agent.reconcile(desired(tenant()), now=1000)

        assert report["tenants"][0]["stats"] == {"pages": 3}

    def test_not_collected_while_stopped(self, agent, docker):
        agent.reconcile(desired(tenant(state="stopped")), now=1000)

        assert self.stats_calls(docker) == []
