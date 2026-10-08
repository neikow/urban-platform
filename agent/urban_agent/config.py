import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    control_plane_url: str
    token: str
    state_dir: Path
    # Only images under this name are ever run: the control plane cannot make
    # a host run anything else, whatever it sends.
    image: str = "ghcr.io/neikow/urban-platform"
    poll_seconds: int = 30
    # A failed deployment is tried again after this delay, not at every poll.
    retry_seconds: int = 300
    # The websites' figures (pages, users) are collected this often.
    stats_seconds: int = 900
    # Plain HTTP to the control plane, for local development only.
    insecure: bool = False

    @classmethod
    def from_environment(cls, environ: dict[str, str]) -> "Config":
        url = environ.get("CONTROL_PLANE_URL", "").rstrip("/")
        token = environ.get("AGENT_TOKEN", "")
        insecure = environ.get("AGENT_INSECURE", "") == "1"
        if not url or not token:
            raise ConfigError("CONTROL_PLANE_URL and AGENT_TOKEN are required.")
        if urlsplit(url).scheme != "https" and not insecure:
            raise ConfigError("CONTROL_PLANE_URL must be https (AGENT_INSECURE=1 for development).")
        return cls(
            control_plane_url=url,
            token=token,
            state_dir=Path(environ.get("AGENT_STATE_DIR", "/var/lib/urban-agent")),
            image=environ.get("AGENT_IMAGE", cls.image),
            poll_seconds=int(environ.get("AGENT_POLL_SECONDS", cls.poll_seconds)),
            retry_seconds=int(environ.get("AGENT_RETRY_SECONDS", cls.retry_seconds)),
            stats_seconds=int(environ.get("AGENT_STATS_SECONDS", cls.stats_seconds)),
            insecure=insecure,
        )


def from_environment() -> Config:
    return Config.from_environment(dict(os.environ))
