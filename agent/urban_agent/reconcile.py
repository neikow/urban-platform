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
    tenants/<slug>/state.json    the generation applied, its outcome, its version
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

from . import VERSION
from .config import Config
from .docker import Docker, DockerError

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


@dataclass
class TenantStatus:
    slug: str
    generation: int | None = None  # the generation last applied successfully
    attempted: int | None = None  # the generation last tried
    status: str = "unknown"  # running, stopped, failed, absent, unknown
    version: str = ""  # reported by /healthz/ after the last deployment
    error: str = ""
    failed_at: float = 0
    services: dict[str, str] = field(default_factory=dict)
    # The website's figures (manage.py tenant_stats), and when they were collected.
    stats: dict[str, int] = field(default_factory=dict)
    stats_at: float = 0


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
    def __init__(self, config: Config, docker: Docker | None = None) -> None:
        self.config = config
        self.docker = docker or Docker()
        self.tenants_dir = config.state_dir / "tenants"
        self.edge_hash = ""

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

    def apply(self, tenant: Tenant, now: float) -> TenantStatus:
        status = self.load_status(tenant.slug)
        try:
            if tenant.state == "absent":
                return self._remove(tenant, status)
            if tenant.state == "running":
                up_to_date = status.generation == tenant.generation and status.status == "running"
                waiting = (
                    status.status == "failed"
                    and status.attempted == tenant.generation
                    and now - status.failed_at < self.config.retry_seconds
                )
                if not up_to_date and not waiting:
                    status.attempted = tenant.generation
                    status.stats_at = 0  # fresh figures after a deployment
                    self.deploy(tenant, status)
                    status.generation, status.status, status.error = (
                        tenant.generation,
                        "running",
                        "",
                    )
            elif status.status != "stopped":
                compose_files, env_file = self._files(tenant.slug)
                if compose_files[0].exists():
                    self.docker.compose(tenant.slug, compose_files, env_file, ["stop"])
                status.generation, status.status, status.error = tenant.generation, "stopped", ""
        except (DockerError, OSError) as error:
            logger.error("%s: %s", tenant.slug, error)
            status.status = "failed"
            status.error = str(error)[:2000]
            status.failed_at = now
        self.save_status(status)
        self.observe(status)
        return status

    def _remove(self, tenant: Tenant, status: TenantStatus) -> TenantStatus:
        compose_files, env_file = self._files(tenant.slug)
        if compose_files[0].exists():
            args = ["down", "--remove-orphans"] + (["--volumes"] if tenant.purge else [])
            self.docker.compose(tenant.slug, compose_files, env_file, args, timeout=300)
        shutil.rmtree(self._dir(tenant.slug), ignore_errors=True)
        return TenantStatus(slug=tenant.slug, generation=tenant.generation, status="absent")

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

        return {
            "agent_version": VERSION,
            "edge": edge,
            "errors": errors,
            "tenants": [
                {
                    k: v
                    for k, v in asdict(s).items()
                    if k not in ("attempted", "failed_at", "stats_at")
                }
                for s in statuses.values()
            ],
        }
