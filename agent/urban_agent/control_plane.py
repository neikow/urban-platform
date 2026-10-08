"""The control plane's agent API (version 1, see agent/README.md)."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Config

TIMEOUT_SECONDS = 20


class ControlPlaneError(Exception):
    pass


class ControlPlane:
    def __init__(self, config: Config) -> None:
        self.base = f"{config.control_plane_url}/api/agent/v1"
        self.token = config.token

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        request = Request(
            f"{self.base}/{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            # The URL is the configured control plane (https enforced by Config).
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
                payload = response.read()
        except HTTPError as error:
            raise ControlPlaneError(f"{method} {path}: HTTP {error.code}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise ControlPlaneError(f"{method} {path}: {error}") from error
        try:
            return json.loads(payload) if payload else None
        except ValueError as error:
            raise ControlPlaneError(f"{method} {path}: not JSON") from error

    def desired_state(self) -> dict[str, Any]:
        state = self._call("GET", "desired-state")
        if not isinstance(state, dict):
            raise ControlPlaneError("desired-state: not an object")
        return state

    def report(self, report: dict[str, Any]) -> None:
        self._call("POST", "report", report)
