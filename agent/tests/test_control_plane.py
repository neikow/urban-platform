import json
import threading
from typing import Any
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from urban_agent.config import Config, ConfigError
from urban_agent.control_plane import ControlPlane, ControlPlaneError


class FakeControlPlane(BaseHTTPRequestHandler):
    desired: dict[str, Any] = {"edge": {}, "tenants": []}
    reports: list[dict[str, Any]] = []

    def _authorized(self) -> bool:
        if self.headers.get("Authorization") != "Bearer secret":
            self.send_response(401)
            self.end_headers()
            return False
        return True

    def do_GET(self) -> None:
        if not self._authorized():
            return
        body = json.dumps(self.desired).encode()
        self.send_response(200 if self.path == "/api/agent/v1/desired-state" else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._authorized():
            return
        length = int(self.headers["Content-Length"])
        self.reports.append(json.loads(self.rfile.read(length)))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), FakeControlPlane)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    FakeControlPlane.reports = []
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def client(url, token="secret"):
    return ControlPlane(
        Config(control_plane_url=url, token=token, state_dir=None, insecure=True)  # type: ignore[arg-type]
    )


def test_desired_state_and_report(server):
    FakeControlPlane.desired = {"edge": {"acme_email": "ops@example.org"}, "tenants": []}
    control_plane = client(server)

    assert control_plane.desired_state()["edge"]["acme_email"] == "ops@example.org"
    control_plane.report({"agent_version": "dev", "tenants": []})
    assert FakeControlPlane.reports == [{"agent_version": "dev", "tenants": []}]


def test_wrong_token(server):
    with pytest.raises(ControlPlaneError, match="401"):
        client(server, token="nope").desired_state()


def test_unreachable():
    with pytest.raises(ControlPlaneError):
        client("http://127.0.0.1:9").desired_state()


class TestConfig:
    def test_requires_https(self):
        with pytest.raises(ConfigError):
            Config.from_environment(
                {"CONTROL_PLANE_URL": "http://cp.example.org", "AGENT_TOKEN": "t"}
            )

    def test_insecure_for_development(self):
        config = Config.from_environment(
            {
                "CONTROL_PLANE_URL": "http://localhost:8000/",
                "AGENT_TOKEN": "t",
                "AGENT_INSECURE": "1",
            }
        )

        assert config.control_plane_url == "http://localhost:8000"

    def test_requires_a_token(self):
        with pytest.raises(ConfigError):
            Config.from_environment({"CONTROL_PLANE_URL": "https://cp.example.org"})
