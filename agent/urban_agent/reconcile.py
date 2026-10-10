"""Bring the host in line with the desired state, one website at a time.

The control plane says, for each website: its release, its variables, and
whether it should run, be stopped, or be removed. The agent never acts on
what is *not* said: a website missing from the desired state is left as it
is, so an empty answer (a bug, a restored backup) cannot take sites down.
Data is deleted only for a website marked absent *and* purge.

Files, under the state directory:

    tenants/<slug>/compose.yml   from the website's image (deploy/tenant/compose.yml)
    tenants/<slug>/compose.override.yml
                                 written by the agent with the "external" edge:
                                 nginx joins the proxy's network as <slug>-nginx,
                                 or is published on 127.0.0.1:<http_port>
    tenants/<slug>/.env          its variables (mode 0600: it holds secrets)
    tenants/<slug>/state.json    the generation applied, its outcome, its version, and a
                                 hash of what was deployed (``Tenant.spec``)
    journal.json                 the events not yet sent to the control plane (journal.py)
"""

import hashlib
import json
import logging
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import VERSION, resources
from .commands import Commands
from .config import Config
from .docker import Docker, DockerError
from .hints import hint
from .journal import Journal

logger = logging.getLogger(__name__)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
ENV_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
TAG = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
STATES = ("running", "stopped", "absent")
# Set by the agent from its own configuration, never by the control plane.
RESERVED_KEYS = {"IMAGE", "IMAGE_TAG", "TENANT_SLUG"}
COMPOSE_PATH_IN_IMAGE = "/app/deploy/tenant/compose.yml"
EDGE_COMPOSE = Path(__file__).parent / "edge" / "compose.yml"
EDGE_PROJECT = "urban-edge"
EDGE_NETWORK = "urban-edge"
DEPLOY_TIMEOUT = 20 * 60
# "traefik": the agent runs Traefik on 80/443 with Let's Encrypt certificates.
# "external": the host already has a reverse proxy, with its own certificates.
# With a "network" (a proxy running in Docker), each website's nginx joins it as
# <slug>-nginx; without, it is published on 127.0.0.1:<http_port>.
EDGE_MODES = ("traefik", "external")
NETWORK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
# The end of a failing service's logs, sent with the failure.
LOG_LINES = 60
LOG_CHARS = 4000
LOG_SERVICES = 3


class InvalidTenant(Exception):
    pass


@dataclass
class Tenant:
    slug: str
    generation: int
    state: str
    image_tag: str
    env: dict[str, str]
    purge: bool = False
    http_port: int | None = None
    # The host proxy's Docker network (external edge), set from the edge settings.
    proxy_network: str | None = None

    @classmethod
    def parse(cls, data: Any) -> "Tenant":
        """A website of the desired state, checked before anything reaches Docker."""
        if not isinstance(data, dict):
            raise InvalidTenant("not an object")
        slug = data.get("slug")
        if not isinstance(slug, str) or not SLUG.match(slug):
            raise InvalidTenant(f"invalid slug {slug!r}")
        state = data.get("state", "running")
        if state not in STATES:
            raise InvalidTenant(f"{slug}: invalid state {state!r}")
        generation = data.get("generation")
        if not isinstance(generation, int) or isinstance(generation, bool):
            raise InvalidTenant(f"{slug}: invalid generation")
        image_tag = data.get("image_tag", "")
        env = data.get("env") or {}
        http_port = data.get("http_port")
        if http_port is not None and (
            not isinstance(http_port, int)
            or isinstance(http_port, bool)
            or not 1024 <= http_port <= 65535
        ):
            raise InvalidTenant(f"{slug}: invalid http_port {http_port!r}")
        if state != "absent":
            if not isinstance(image_tag, str) or not TAG.match(image_tag):
                raise InvalidTenant(f"{slug}: invalid image_tag {image_tag!r}")
            if not isinstance(env, dict):
                raise InvalidTenant(f"{slug}: env is not an object")
            for key, value in env.items():
                if not isinstance(key, str) or not ENV_KEY.match(key) or key in RESERVED_KEYS:
                    raise InvalidTenant(f"{slug}: variable {key!r} not allowed")
                # Written single-quoted (literal, no interpolation): no quote, no newline.
                if not isinstance(value, str) or "'" in value or "\n" in value or "\r" in value:
                    raise InvalidTenant(f"{slug}: invalid value for {key}")
        return cls(
            slug=slug,
            generation=generation,
            state=state,
            image_tag=image_tag if isinstance(image_tag, str) else "",
            env={str(k): str(v) for k, v in env.items()} if isinstance(env, dict) else {},
            purge=data.get("purge") is True,
            http_port=http_port,
        )

    def spec(self) -> str:
        """A hash of what a deployment applies. Generations restart at 1 when a website is
        created again with an earlier one's slug: a website with other secrets is another
        website, whatever its generation."""
        values = [self.image_tag, self.env, self.http_port, self.proxy_network]
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


@dataclass
class TenantStatus:
    slug: str
    generation: int | None = None  # the generation last applied successfully
    attempted: int | None = None  # the generation last tried
    spec: str = ""  # Tenant.spec of the last successful deployment
    status: str = "unknown"  # running, stopped, failed, absent, unknown
    version: str = ""  # reported by /healthz/ after the last deployment
    error: str = ""
    failed_at: float = 0
    services: dict[str, str] = field(default_factory=dict)
    # Services in trouble (unhealthy, exited with an error…), and why.
    problems: dict[str, str] = field(default_factory=dict)
    # With a failure: its known cause, if any, and the end of the failing services' logs.
    hint: str = ""
    logs: dict[str, str] = field(default_factory=dict)
    # The website's figures (manage.py tenant_stats), and when they were collected.
    stats: dict[str, int] = field(default_factory=dict)
    stats_at: float = 0
    # Memory its containers use, in bytes (collected with the host's resources).
    memory: int = 0


def service_problem(service: dict[str, Any]) -> str:
    """What is wrong with a container of ``docker compose ps``, or ""."""
    state, code = service.get("State"), service.get("ExitCode")
    if service.get("Health") == "unhealthy":
        return "unhealthy"
    if state in ("restarting", "dead"):
        return str(state)
    if state == "exited" and code not in (0, None):
        return f"exited with code {code}"
    return ""


def env_file_content(tenant: Tenant, image: str) -> str:
    values = {
        **tenant.env,
        "TENANT_SLUG": tenant.slug,
        "IMAGE": image,
        "IMAGE_TAG": tenant.image_tag,
    }
    # Single quotes: Compose takes the value literally ($ in a secret stays $).
    return "".join(f"{key}='{value}'\n" for key, value in sorted(values.items()))


class Reconciler:
    def __init__(
        self, config: Config, docker: Docker | None = None, journal: Journal | None = None
    ) -> None:
        self.config = config
        self.docker = docker or Docker()
        self.journal = journal or Journal(config.state_dir / "journal.json")
        self.tenants_dir = config.state_dir / "tenants"
        self.edge_hash = ""
        self.edge = ""
        self.errors: list[str] = []
        # The host's resources and the websites' memory, every ``stats_seconds``.
        self.resources: dict[str, Any] = {}
        self.memory: dict[str, int] = {}
        self.resources_at = 0.0
        self.commands = Commands(config.state_dir / "commands.json")

    # --- Files --------------------------------------------------------------------

    def _dir(self, slug: str) -> Path:
        return self.tenants_dir / slug

    def load_status(self, slug: str) -> TenantStatus:
        try:
            data = json.loads((self._dir(slug) / "state.json").read_text())
            return TenantStatus(**{**data, "slug": slug})
        except (OSError, ValueError, TypeError):
            return TenantStatus(slug=slug)

    def save_status(self, status: TenantStatus) -> None:
        path = self._dir(status.slug) / "state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(status), indent=2))

    def managed_slugs(self) -> list[str]:
        if not self.tenants_dir.is_dir():
            return []
        return sorted(p.name for p in self.tenants_dir.iterdir() if (p / "state.json").exists())

    def _files(self, slug: str) -> tuple[list[Path], Path]:
        """The Compose files of a website (with the agent's override, if any), its .env."""
        directory = self._dir(slug)
        files = [directory / "compose.yml", directory / "compose.override.yml"]
        return [f for f in files if f == files[0] or f.exists()], directory / ".env"

    # --- One website --------------------------------------------------------------

    def deploy(self, tenant: Tenant, status: TenantStatus) -> None:
        image = f"{self.config.image}:{tenant.image_tag}"
        self.docker.pull(image)
        self.docker.pull(f"{self.config.image}-nginx:{tenant.image_tag}")
        compose = self.docker.read_file(image, COMPOSE_PATH_IN_IMAGE)

        directory = self._dir(tenant.slug)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "compose.yml").write_text(compose)
        override = directory / "compose.override.yml"
        if tenant.proxy_network:
            override.write_text(
                "# Written by the agent: the host's reverse proxy reaches this website\n"
                f"# as {tenant.slug}-nginx on its network.\n"
                "services:\n  nginx:\n    networks:\n      proxy:\n"
                f'        aliases: ["{tenant.slug}-nginx"]\n'
                f"networks:\n  proxy:\n    name: {tenant.proxy_network}\n    external: true\n"
            )
        elif tenant.http_port:
            override.write_text(
                "# Written by the agent: the host's reverse proxy forwards to this port.\n"
                "services:\n  nginx:\n    ports:\n"
                f'      - "127.0.0.1:{tenant.http_port}:80"\n'
            )
        else:
            override.unlink(missing_ok=True)
        compose_files, env_file = self._files(tenant.slug)
        env_file.touch(mode=0o600)
        env_file.chmod(0o600)
        env_file.write_text(env_file_content(tenant, self.config.image))

        self.docker.ensure_network(EDGE_NETWORK)
        # --wait: returns once the services are healthy and the one-shot jobs
        # (migrations, bootstrap) exited successfully, fails otherwise.
        self.docker.compose(
            tenant.slug,
            compose_files,
            env_file,
            ["up", "--detach", "--wait", "--remove-orphans"],
            timeout=DEPLOY_TIMEOUT,
        )
        status.version = self.health_version(tenant.slug)

    def health_version(self, slug: str) -> str:
        compose_files, env_file = self._files(slug)
        probe = (
            "import json, os, urllib.request as r; print(json.load(r.urlopen(r.Request("
            "'http://localhost:8000/healthz/', headers={'Host': os.environ['ALLOWED_HOSTS'], "
            "'X-Forwarded-Proto': 'https'}), timeout=5))['version'])"
        )
        out = self.docker.compose(
            slug, compose_files, env_file, ["exec", "-T", "web", "python", "-c", probe]
        )
        return out.strip()

    def collect_stats(self, status: TenantStatus, now: float) -> None:
        """The website's figures, every ``stats_seconds`` while it runs."""
        if status.status != "running" or now - status.stats_at < self.config.stats_seconds:
            return
        status.stats_at = now  # failed or not: not again before the next interval
        compose_files, env_file = self._files(status.slug)
        try:
            out = self.docker.compose(
                status.slug,
                compose_files,
                env_file,
                ["exec", "-T", "web", "python", "manage.py", "tenant_stats"],
            )
            data = json.loads(out.strip().splitlines()[-1])
        except (DockerError, OSError, ValueError, IndexError) as error:
            # Releases before the command have no figures.
            logger.warning("%s: no figures: %s", status.slug, error)
        else:
            if isinstance(data, dict):
                status.stats = {str(k): v for k, v in data.items() if type(v) is int and v >= 0}
        self.save_status(status)

    def observe(self, status: TenantStatus) -> None:
        """The containers' states, for the report."""
        compose_files, env_file = self._files(status.slug)
        if not compose_files[0].exists():
            return
        try:
            services = self.docker.compose_services(status.slug, compose_files, env_file)
        except (DockerError, ValueError) as error:
            status.services = {}
            logger.warning("%s: could not list containers: %s", status.slug, error)
            return
        status.services = {
            s.get("Service", "?"): s.get("Health") or s.get("State", "?") for s in services
        }
        problems = {
            str(s.get("Service", "?")): problem for s in services if (problem := service_problem(s))
        }
        if problems == status.problems:
            return
        # A failed deployment has its own event; a running website changing is news.
        if status.status == "running":
            if problems:
                self.journal.record(
                    "warning",
                    ", ".join(f"{name} {problem}" for name, problem in sorted(problems.items())),
                    status.slug,
                    detail=self.service_logs(status.slug, list(problems), compose_files, env_file),
                )
            else:
                self.journal.record("info", "All services are back to normal.", status.slug)
        status.problems = problems
        self.save_status(status)

    def service_logs(
        self, slug: str, services: list[str], compose_files: list[Path], env_file: Path
    ) -> str:
        return "\n\n".join(
            f"--- {name}\n{text}"
            for name, text in self.logs(slug, services, compose_files, env_file).items()
        )

    def logs(
        self, slug: str, services: list[str], compose_files: list[Path], env_file: Path
    ) -> dict[str, str]:
        """The end of these services' logs (at most LOG_SERVICES of them)."""
        found = {}
        for name in sorted(services)[:LOG_SERVICES]:
            try:
                out = self.docker.compose(
                    slug,
                    compose_files,
                    env_file,
                    ["logs", "--no-color", "--no-log-prefix", "--tail", str(LOG_LINES), name],
                )
            except DockerError as error:
                out = f"(no logs: {error})"
            found[name] = out.strip()[-LOG_CHARS:]
        return found

    def setup_warnings(self, slug: str) -> list[str]:
        """What the website's setup (bootstrap_tenant, in the migrator) could not do."""
        compose_files, env_file = self._files(slug)
        text = self.logs(slug, ["migrator"], compose_files, env_file).get("migrator", "")
        marker = "WARNING: "
        return [line.split(marker, 1)[1] for line in text.splitlines() if marker in line][:20]

    def failure_logs(self, slug: str) -> dict[str, str]:
        """After a failed deployment: the logs of the services that failed."""
        compose_files, env_file = self._files(slug)
        if not compose_files[0].exists() or not env_file.exists():
            return {}
        try:
            services = self.docker.compose_services(slug, compose_files, env_file)
        except (DockerError, ValueError):
            return {}
        failing = [str(s.get("Service", "?")) for s in services if service_problem(s)]
        return self.logs(slug, failing, compose_files, env_file)

    def apply(self, tenant: Tenant, now: float) -> TenantStatus:
        status = self.load_status(tenant.slug)
        try:
            if tenant.state == "absent":
                return self._remove(tenant, status)
            if tenant.state == "running":
                spec = tenant.spec()
                applied = status.generation == tenant.generation and status.status == "running"
                if applied and not status.spec:
                    status.spec = spec  # deployed by an agent before the hash: taken as is
                up_to_date = applied and status.spec == spec and self.containers_exist(tenant.slug)
                waiting = (
                    status.status == "failed"
                    and status.attempted == tenant.generation
                    and now - status.failed_at < self.config.retry_seconds
                )
                if not up_to_date and not waiting:
                    status.attempted = tenant.generation
                    status.stats_at = 0  # fresh figures after a deployment
                    started = time.monotonic()
                    self.deploy(tenant, status)
                    status.generation, status.status, status.error = (
                        tenant.generation,
                        "running",
                        "",
                    )
                    status.spec = spec
                    status.hint, status.logs, status.problems = "", {}, {}
                    message = (
                        f"Deployed {tenant.image_tag} (generation {tenant.generation}, "
                        f"version {status.version or '?'}) in {time.monotonic() - started:.0f} s."
                    )
                    warnings = self.setup_warnings(tenant.slug)
                    if warnings:
                        message += f" {len(warnings)} warning(s) from the setup: {warnings[0]}"
                    self.journal.record(
                        "warning" if warnings else "info",
                        message,
                        tenant.slug,
                        detail="\n".join(warnings),
                    )
            elif status.status != "stopped":
                compose_files, env_file = self._files(tenant.slug)
                if compose_files[0].exists():
                    self.docker.compose(tenant.slug, compose_files, env_file, ["stop"])
                status.generation, status.status, status.error = tenant.generation, "stopped", ""
                status.hint, status.logs = "", {}
                self.journal.record("info", "Stopped.", tenant.slug)
        except (DockerError, OSError) as error:
            self.fail(tenant, status, str(error), now)
        self.save_status(status)
        self.observe(status)
        return status

    def containers_exist(self, slug: str) -> bool:
        """Whether a deployed website still has containers: removed behind the agent's back
        (by hand, a prune), it is deployed again."""
        compose_files, env_file = self._files(slug)
        try:
            if self.docker.compose_services(slug, compose_files, env_file):
                return True
        except (DockerError, ValueError) as error:
            logger.warning("%s: could not list containers: %s", slug, error)
            return True  # unknown: left as it is
        self.journal.record("warning", "Its containers are gone: deploying it again.", slug)
        return False

    def fail(self, tenant: Tenant, status: TenantStatus, error: str, now: float) -> None:
        previous = (status.status, status.error)
        status.status = "failed"
        status.error = error[:2000]
        status.failed_at = now
        status.logs = self.failure_logs(tenant.slug) if tenant.state == "running" else {}
        status.hint = hint(error, *status.logs.values())
        if previous == ("failed", status.error):
            logger.error("%s: %s", tenant.slug, error)  # the same failure again: no new event
            return
        action = {"running": "Deployment", "stopped": "Stop", "absent": "Removal"}[tenant.state]
        logs = "\n\n".join(f"--- {name}\n{text}" for name, text in status.logs.items())
        summary = status.hint or (error.strip().splitlines() or ["?"])[-1]
        self.journal.record(
            "error",
            f"{action} failed: {summary}",
            tenant.slug,
            detail=f"{error}\n\n{logs}".strip(),
        )

    def _remove(self, tenant: Tenant, status: TenantStatus) -> TenantStatus:
        compose_files, env_file = self._files(tenant.slug)
        if compose_files[0].exists():
            args = ["down", "--remove-orphans"] + (["--volumes"] if tenant.purge else [])
            self.docker.compose(tenant.slug, compose_files, env_file, args, timeout=300)
        if self._dir(tenant.slug).exists():  # not when already removed
            self.journal.record(
                "info", "Removed with its data." if tenant.purge else "Removed.", tenant.slug
            )
        shutil.rmtree(self._dir(tenant.slug), ignore_errors=True)
        return TenantStatus(slug=tenant.slug, generation=tenant.generation, status="absent")

    def collect_resources(self, now: float) -> None:
        """The host's resources and the websites' memory, every ``stats_seconds``."""
        if self.resources_at and now - self.resources_at < self.config.stats_seconds:
            return
        self.resources_at = now
        self.resources = resources.host(self.config.state_dir)
        try:
            self.memory = self.docker.project_memory()
        except (DockerError, ValueError) as error:
            logger.warning("no memory figures: %s", error)

    # --- The edge proxy -----------------------------------------------------------

    def ensure_edge(self, edge: dict[str, Any]) -> str:
        """The host's edge: our Traefik, or the host's own reverse proxy ("external")."""
        mode = edge.get("mode", "traefik")
        if mode not in EDGE_MODES:
            return f"invalid mode {mode!r}"
        email = edge.get("acme_email", "")
        if not isinstance(email, str) or "'" in email or "\n" in email:
            return "invalid acme_email"
        env_file = self.config.state_dir / "edge.env"
        # Traefik's file needs an email even to be stopped.
        content = f"ACME_EMAIL='{email or 'unused@example.org'}'\nEDGE_NETWORK='{EDGE_NETWORK}'\n"
        digest = hashlib.sha256((mode + content + EDGE_COMPOSE.read_text()).encode()).hexdigest()
        if digest == self.edge_hash:
            return "running" if mode == "traefik" else "external"
        try:
            # The websites' Compose file joins this network in both modes.
            self.docker.ensure_network(EDGE_NETWORK)
            env_file.parent.mkdir(parents=True, exist_ok=True)
            env_file.write_text(content)
            if mode == "traefik":
                if not email:
                    return "acme_email required"
                self.docker.compose(
                    EDGE_PROJECT, [EDGE_COMPOSE], env_file, ["up", "--detach", "--wait"]
                )
            else:
                # Free ports 80/443 for the host's proxy if our Traefik ran before.
                self.docker.compose(EDGE_PROJECT, [EDGE_COMPOSE], env_file, ["down"])
        except (DockerError, OSError) as error:
            logger.error("edge: %s", error)
            return f"failed: {error}"[:500]
        self.edge_hash = digest
        return "running" if mode == "traefik" else "external"

    # --- The whole host -----------------------------------------------------------

    def reconcile(self, desired: dict[str, Any], now: float | None = None) -> dict[str, Any]:
        """Apply the desired state; returns the report for the control plane."""
        now = time.time() if now is None else now
        statuses: dict[str, TenantStatus] = {}
        errors: list[str] = []
        edge_settings = desired.get("edge") or {}
        if not isinstance(edge_settings, dict):
            edge_settings = {}
        external = edge_settings.get("mode") == "external"
        network = edge_settings.get("network") if external else None
        if network is not None and (not isinstance(network, str) or not NETWORK.match(network)):
            errors.append(f"invalid proxy network {network!r}")
            network = None
        edge = self.ensure_edge(edge_settings)
        if edge != self.edge:
            if edge not in ("running", "external"):
                self.journal.record("error", f"Edge: {edge}")
            elif self.edge:
                self.journal.record("info", f"Edge: {edge}.")
            self.edge = edge

        ports: dict[int, str] = {}
        for data in desired.get("tenants") or []:
            try:
                tenant = Tenant.parse(data)
                if tenant.state != "absent" and external and network:
                    tenant.proxy_network = network
                    tenant.http_port = None  # reached by name on the network
                elif tenant.state != "absent" and external:
                    if tenant.http_port is None:
                        raise InvalidTenant(f"{tenant.slug}: http_port required (external edge)")
                    if tenant.http_port in ports:
                        raise InvalidTenant(
                            f"{tenant.slug}: http_port {tenant.http_port} "
                            f"already used by {ports[tenant.http_port]}"
                        )
                    ports[tenant.http_port] = tenant.slug
                elif not external:
                    tenant.http_port = None  # Traefik routes by hostname: no port
            except InvalidTenant as error:
                errors.append(str(error))
                continue
            statuses[tenant.slug] = self.apply(tenant, now)

        # Websites the desired state does not mention: reported, left alone.
        for slug in self.managed_slugs():
            if slug not in statuses:
                status = self.load_status(slug)
                self.observe(status)
                statuses[slug] = status

        for status in statuses.values():
            self.collect_stats(status, now)
        self.collect_resources(now)
        for status in statuses.values():
            status.memory = self.memory.get(status.slug, 0) if status.status == "running" else 0

        commands = self.commands.run(desired.get("commands"), self, errors, now)

        for message in errors:
            if message not in self.errors:
                self.journal.record("error", f"Desired state: {message}")
        self.errors = errors

        return {
            "agent_version": VERSION,
            "edge": edge,
            "host": self.resources,
            "errors": errors,
            "tenants": [
                {
                    k: v
                    for k, v in asdict(s).items()
                    if k not in ("attempted", "spec", "failed_at", "stats_at", "problems")
                }
                for s in statuses.values()
            ],
            "commands": commands,
            "journal": self.journal.id,
            "events": self.journal.pending(),
        }
