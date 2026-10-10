"""What the host has left: memory, disk, processors, load. The control plane warns
before a host fills up, and tells how many more websites it can take.

Read from inside the agent's container: ``/proc/meminfo`` and the load average are the
host's (containers share its kernel), the disk is the one holding the agent's state
directory, a Docker volume: the disk of Docker's data, where the websites' are too.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Any

UNITS = {
    "b": 1,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
}
SIZE = re.compile(r"^\s*([0-9.]+)\s*([a-z]+)\s*$", re.IGNORECASE)


def size(text: str) -> int:
    """Bytes of ``docker stats``' "123.4MiB"."""
    match = SIZE.match(text)
    if not match or match.group(2).lower() not in UNITS:
        raise ValueError(f"not a size: {text!r}")
    return int(float(match.group(1)) * UNITS[match.group(2).lower()])


def meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    """MemTotal and MemAvailable, in bytes."""
    values = {}
    for line in path.read_text().splitlines():
        name, _, rest = line.partition(":")
        if name in ("MemTotal", "MemAvailable"):
            values[name] = int(rest.split()[0]) * 1024  # kB
    return values


def host(state_dir: Path, meminfo_path: Path = Path("/proc/meminfo")) -> dict[str, Any]:
    """The host's resources, in bytes; what cannot be read is left out."""
    found: dict[str, Any] = {}
    try:
        memory = meminfo(meminfo_path)
        found["memory_total"] = memory["MemTotal"]
        found["memory_available"] = memory["MemAvailable"]
    except (OSError, ValueError, KeyError, IndexError):
        pass
    try:
        disk = shutil.disk_usage(state_dir)
        found["disk_total"], found["disk_free"] = disk.total, disk.free
    except OSError:
        pass
    found["cpus"] = os.cpu_count() or 0
    try:
        found["load"] = round(os.getloadavg()[0], 2)
    except OSError:
        pass
    return found
