"""Known causes of a failed deployment, said plainly (for the control plane's users)."""

import re

HINTS = [
    (
        r"password authentication failed for user",
        "The database refused the website's password: its data was most likely left by "
        "an earlier website with the same slug, removed without its data. Delete that data "
        "(remove the website with its data, then deploy again), or use another slug.",
    ),
    (
        r"port is already allocated|address already in use",
        "A port this website needs is already used by another program on the host.",
    ),
    (
        r"manifest unknown|manifest for .* not found|pull access denied",
        "This release does not exist in the registry: check its tag.",
    ),
    (r"no space left on device", "The host's disk is full."),
    (
        r"network .* not found|network .* declared as external, but could not be found",
        "The reverse proxy's Docker network does not exist on the host.",
    ),
    (
        r"InconsistentMigrationHistory|Migration .* is applied before its dependency",
        "The database's migrations do not match this release: was an older release "
        "deployed over a newer one?",
    ),
    (
        r"is already in use by container",
        "A container with this website's name exists outside its Compose project: "
        "remove it on the host.",
    ),
    (r"timed out after", "The deployment took too long: the host may be overloaded."),
    (r"Cannot connect to the Docker daemon", "Docker is not running on the host."),
]


def hint(*texts: str) -> str:
    """The first known cause found in ``texts`` (error, logs), or ""."""
    joined = "\n".join(texts)
    for pattern, explanation in HINTS:
        if re.search(pattern, joined, re.IGNORECASE):
            return explanation
    return ""
