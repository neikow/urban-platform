import pytest

from urban_agent import resources
from urban_agent.docker import Docker


@pytest.mark.parametrize(
    "text, expected",
    [("123.4MiB", 129_394_278), ("1.5GiB", 1_610_612_736), ("512kB", 512_000), ("0B", 0)],
)
def test_size(text, expected):
    assert resources.size(text) == expected


def test_size_rejects():
    with pytest.raises(ValueError):
        resources.size("lots")


def test_host(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:  8000000 kB\nMemFree: 1000 kB\nMemAvailable:  2000000 kB\n")

    found = resources.host(tmp_path, meminfo)

    assert found["memory_total"] == 8_192_000_000
    assert found["memory_available"] == 2_048_000_000
    assert found["disk_total"] >= found["disk_free"] > 0
    assert found["cpus"] >= 1


def test_host_without_meminfo(tmp_path):
    found = resources.host(tmp_path, tmp_path / "missing")

    assert "memory_total" not in found and "disk_free" in found


def test_project_memory(monkeypatch):
    outputs = {
        "ps": "abc123abc123\taix\ndef456def456\taix\n999999999999\tarles\n",
        "stats": "abc123abc123\t100MiB / 7.6GiB\ndef456def456\t50MiB / 7.6GiB\n"
        "999999999999\t-- / --\n",
    }
    monkeypatch.setattr(Docker, "run", lambda self, args, timeout=120: outputs[args[0]])

    assert Docker().project_memory() == {"aix": 150 * 1024**2}
