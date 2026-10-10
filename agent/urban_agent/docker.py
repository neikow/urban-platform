"""The Docker CLI, through one door: easy to replace in tests."""

import json
import logging
import subprocess  # nosec B404: fixed docker commands, no shell
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .resources import size

logger = logging.getLogger(__name__)


class DockerError(Exception):
    pass


class Docker:
    def run(self, args: Sequence[str], timeout: int = 120) -> str:
        try:
            # The docker CLI from PATH: the agent image installs it.
            result = subprocess.run(  # nosec B603 B607
                ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as error:
            raise DockerError(f"docker {args[0]}: timed out after {timeout} s") from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()[-5:]
            raise DockerError(f"docker {' '.join(args[:3])}: " + " / ".join(detail))
        return result.stdout

    def version(self) -> str:
        return self.run(["version", "--format", "{{.Server.Version}}"]).strip()

    def pull(self, image: str) -> None:
        """The image from its registry, or the copy already here when the registry fails."""
        try:
            self.run(["pull", "--quiet", image], timeout=900)
        except DockerError as error:
            try:
                self.run(["image", "inspect", "--format", "{{.Id}}", image])
            except DockerError:
                raise error from None
            logger.warning("Using the local %s: %s", image, error)

    def read_file(self, image: str, path: str) -> str:
        """A file of an image, without starting its usual command."""
        return self.run(["run", "--rm", "--entrypoint", "cat", image, path])

    def ensure_network(self, name: str) -> None:
        names = self.run(["network", "ls", "--format", "{{.Name}}"]).split()
        if name not in names:
            self.run(["network", "create", name])

    def compose(
        self,
        project: str,
        compose_files: Sequence[Path],
        env_file: Path,
        args: Sequence[str],
        timeout: int = 120,
    ) -> str:
        files = [arg for path in compose_files for arg in ("-f", str(path))]
        return self.run(
            ["compose", "-p", project, *files, "--env-file", str(env_file), *args],
            timeout=timeout,
        )

    def project_memory(self) -> dict[str, int]:
        """Memory used by each Compose project's containers, in bytes."""
        listed = self.run(
            [
                "ps",
                "--filter",
                "label=com.docker.compose.project",
                "--format",
                '{{.ID}}\t{{.Label "com.docker.compose.project"}}',
            ]
        )
        projects = dict(line.split("\t", 1) for line in listed.strip().splitlines() if "\t" in line)
        if not projects:
            return {}
        out = self.run(
            ["stats", "--no-stream", "--format", "{{.ID}}\t{{.MemUsage}}", *projects], timeout=60
        )
        memory: dict[str, int] = {}
        for line in out.strip().splitlines():
            container, _, usage = line.partition("\t")
            project = projects.get(container[:12])
            if project is None:
                continue
            try:
                used = size(usage.split("/")[0])
            except ValueError:
                continue
            memory[project] = memory.get(project, 0) + used
        return memory

    def compose_stream(
        self,
        project: str,
        compose_files: Sequence[Path],
        env_file: Path,
        args: Sequence[str],
        stdout: Path | None = None,
        stdin: Path | None = None,
        timeout: int = 3600,
    ) -> None:
        """A Compose command writing its output to ``stdout``, or reading ``stdin``, as
        bytes: database dumps and archives, too big for memory."""
        files = [arg for path in compose_files for arg in ("-f", str(path))]
        command = ["docker", "compose", "-p", project, *files, "--env-file", str(env_file), *args]
        out = stdout.open("wb") if stdout else subprocess.DEVNULL
        source = stdin.open("rb") if stdin else subprocess.DEVNULL
        try:
            result = subprocess.run(  # nosec B603 B607: fixed docker commands, no shell
                command, stdout=out, stdin=source, stderr=subprocess.PIPE, timeout=timeout
            )
        except subprocess.TimeoutExpired as error:
            raise DockerError(f"docker compose {args[0]}: timed out after {timeout} s") from error
        finally:
            for handle in (out, source):
                if not isinstance(handle, int):
                    handle.close()
        if result.returncode != 0:
            detail = result.stderr.decode(errors="replace").strip().splitlines()[-5:]
            raise DockerError(f"docker compose {' '.join(args[:3])}: " + " / ".join(detail))

    def compose_services(
        self, project: str, compose_files: Sequence[Path], env_file: Path
    ) -> list[dict[str, Any]]:
        """State of a project's containers, one-shot jobs included."""
        out = self.compose(project, compose_files, env_file, ["ps", "--all", "--format", "json"])
        services = []
        # One JSON object per line (Compose v2.21+), or a single array before.
        for line in out.strip().splitlines():
            parsed = json.loads(line)
            services.extend(parsed if isinstance(parsed, list) else [parsed])
        return services
