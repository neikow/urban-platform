import math
import random
from dataclasses import dataclass
from typing import Any

import pytest

from core.area_index import AreaQuadtree
from publications.geo import area_contains


@dataclass
class Item:
    name: str
    area: dict[str, Any] | None


def ring(cx: float, cy: float, radius: float, sides: int, rng: random.Random) -> list[list[float]]:
    """An irregular star-shaped ring around (cx, cy)."""
    points = [
        [
            cx + radius * rng.uniform(0.4, 1) * math.cos(2 * math.pi * i / sides),
            cy + radius * rng.uniform(0.4, 1) * math.sin(2 * math.pi * i / sides),
        ]
        for i in range(sides)
    ]
    return [*points, points[0]]


def brute_force(items: list[Item], point: dict[str, Any]) -> Item | None:
    return next((i for i in items if i.area and area_contains(i.area, point)), None)


def point(x: float, y: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [x, y]}


@pytest.mark.parametrize("seed", range(5))
def test_matches_brute_force(seed):
    rng = random.Random(seed)
    items = [
        Item(
            f"area-{i}",
            {
                "type": "Polygon",
                "coordinates": [
                    ring(rng.uniform(5.3, 5.45), rng.uniform(43.25, 43.35), 0.03, 40, rng)
                ],
            },
        )
        for i in range(12)
    ]
    # Overlaps, a hole, an island group and an item without area.
    items.append(
        Item(
            "donut",
            {
                "type": "Polygon",
                "coordinates": [ring(5.38, 43.3, 0.05, 60, rng), ring(5.38, 43.3, 0.01, 20, rng)],
            },
        )
    )
    items.append(
        Item(
            "islands",
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [ring(5.32, 43.27, 0.01, 12, rng)],
                    [ring(5.44, 43.34, 0.01, 12, rng)],
                ],
            },
        )
    )
    items.append(Item("none", None))
    tree = AreaQuadtree(items)

    for _ in range(3000):
        p = point(rng.uniform(5.2, 5.55), rng.uniform(43.15, 43.45))
        assert tree.find(p) is brute_force(items, p)


def test_first_item_wins_where_areas_overlap():
    square = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
    first, second = Item("first", square), Item("second", square)

    assert AreaQuadtree([first, second]).find(point(1, 1)) is first


def test_no_areas():
    tree = AreaQuadtree([Item("none", None)])

    assert tree.find(point(1, 1)) is None
    assert tree.find(None) is None
