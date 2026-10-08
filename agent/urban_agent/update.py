"""The agent updating itself, when the control plane asks (agent/README.md).

A container cannot replace itself: the agent pulls the new image, then starts a short
helper from it (``python -m urban_agent.update <container>``) and stops polling. The
helper reads the agent's container, removes it, and runs the new image with the same
settings: name, restart policy, volumes, variables, networks. If the new one does not
start, it runs the old image again.

Only the agent's own image is ever pulled (AGENT_IMAGE + "-agent"), with a tag checked
like the websites' ones: the control plane cannot make the host run anything else.
"""

import json
import logging
import os
import re
import sys
import time
from typing import Any

from . import VERSION
from .config import Config
from .docker import Docker, DockerError

logger = logging.getLogger(__name__)

TAG = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
HELPER_NAME = "urban-agent-update"
# A version not published yet (the image still building): asked again after this.
RETRY_SECONDS = 600
# The helper should replace this container within seconds; if not, polling resumes.
HANDOVER_SECONDS = 300
SOCKET = "/var/run/docker.sock"


class Updater:
    def __init__(self, config: Config, docker: Docker | None = None) -> None:
        self.config = config
        self.docker = docker or Docker()
        self.tried: dict[str, float] = {}  # version -> when last tried
        self.errors: list[str] = []

    def image(self, tag: str) -> str:
        return f"{self.config.image}-agent:{tag}"

    def wanted(self, spec: Any) -> tuple[str, str] | None:
        """(tag, version) when the control plane asks for another version than this one."""
        if not isinstance(spec, dict):
            return None
        tag, version = spec.get("image_tag"), spec.get("version")
        if not isinstance(tag, str) or not isinstance(version, str) or not version:
            return None
        if version == VERSION:
            return None
        if not TAG.match(tag):
            self.errors.append(f"agent update: invalid tag {tag!r}")
            return None
        return tag, version

    def image_version(self, image: str) -> str:
        env = json.loads(
            self.docker.run(["image", "inspect", "--format", "{{json .Config.Env}}", image])
        )
        for entry in env or []:
            name, _, value = entry.partition("=")
            if name == "AGENT_VERSION":
                return value
        return ""

    def start(self, spec: Any, now: float | None = None) -> bool:
        """Hand over to the helper if an update is due; True once it was started."""
        self.errors = []
        wanted = self.wanted(spec)
        if wanted is None:
            return False
        tag, version = wanted
        now = time.time() if now is None else now
        if now - self.tried.get(version, 0) < RETRY_SECONDS:
            return False
        self.tried[version] = now
        image = self.image(tag)
        container = os.environ.get("HOSTNAME", "")
        try:
            self.docker.pull(image)
            found = self.image_version(image)
            if found != version:
                self.errors.append(
                    f"agent update: {image} is {found or 'unversioned'}, not {version} yet"
                )
                return False
            if not container:
                raise DockerError("not running in a container")
            if self._exists(HELPER_NAME):  # left by an update that went wrong
                self.docker.run(["rm", "-f", HELPER_NAME], timeout=60)
            self.docker.run(
                [
                    "run", "-d", "--rm", "--name", HELPER_NAME,
                    "-v", f"{SOCKET}:{SOCKET}",
                    "--entrypoint", "python",
                    image, "-m", "urban_agent.update", container, image,
                ]
            )  # fmt: skip
        except (DockerError, ValueError) as error:
            self.errors.append(f"agent update to {version}: {error}"[:500])
            return False
        logger.info("Updating to %s: the helper replaces this container.", version)
        return True

    def _exists(self, name: str) -> bool:
        try:
            self.docker.run(["container", "inspect", "--format", "{{.Id}}", name])
        except DockerError:
            return False
        return True


# --- The helper ---------------------------------------------------------------------


def run_args(container: dict[str, Any], image_env: list[str], image: str) -> list[str]:
    """``docker run`` arguments recreating ``container`` (docker inspect) on ``image``.

    The variables the old image set itself (AGENT_VERSION…) are left to the new one.
    """
    config, host = container["Config"], container["HostConfig"]
    args = ["run", "-d", "--name", container["Name"].lstrip("/")]
    restart = (host.get("RestartPolicy") or {}).get("Name") or "unless-stopped"
    args += ["--restart", restart]
    for mount in container.get("Mounts") or []:
        source = mount["Name"] if mount.get("Type") == "volume" else mount["Source"]
        suffix = "" if mount.get("RW", True) else ":ro"
        args += ["-v", f"{source}:{mount['Destination']}{suffix}"]
    inherited = set(image_env)
    for entry in config.get("Env") or []:
        if entry not in inherited:
            args += ["-e", entry]
    networks = list((container.get("NetworkSettings") or {}).get("Networks") or {})
    if networks:
        args += ["--network", networks[0]]
    return [*args, image]


def extra_networks(container: dict[str, Any]) -> list[str]:
    return list((container.get("NetworkSettings") or {}).get("Networks") or {})[1:]


def replace(container_id: str, image: str, docker: Docker | None = None) -> int:
    docker = docker or Docker()
    container = json.loads(docker.run(["container", "inspect", container_id]))[0]
    old_image = container["Image"]
    # What the old image set itself: not carried over, the image sets it again.
    image_env = json.loads(
        docker.run(["image", "inspect", "--format", "{{json .Config.Env}}", old_image])
    )
    name = container["Name"].lstrip("/")

    def start(on: str) -> None:
        docker.run(run_args(container, image_env or [], on), timeout=300)
        for network in extra_networks(container):
            docker.run(["network", "connect", network, name])

    docker.run(["rm", "-f", container_id], timeout=120)
    try:
        start(image)
    except DockerError as error:
        logger.error("The new agent did not start (%s): back to the old one.", error)
        try:
            docker.run(["rm", "-f", name], timeout=120)
        except DockerError:
            pass
        start(old_image)
        return 1
    logger.info("Agent %s replaced by %s.", name, image)
    return 0


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(argv) != 2:
        logger.error("usage: python -m urban_agent.update <container> <image>")
        return 2
    return replace(argv[0], argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
