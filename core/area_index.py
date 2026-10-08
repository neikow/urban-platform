"""Quadtree over areas (GeoJSON Polygon / MultiPolygon), to find the area containing a point.

Built once per matching run, then queried for every user. The space covered by
the areas is split into quadrants until each cell is either:

- crossed by no area edge: the cell lies wholly inside or outside each area,
  so its answer is known when building, and a lookup is a few comparisons;
- crossed by few edges (or at the depth limit): only there do lookups run the
  exact point-in-polygon test, on the areas whose edges cross the cell.

Most residents live away from the area borders, so most lookups test no polygon.
"""

from collections.abc import Sequence
from typing import Any, Generic, Protocol, TypeVar

from publications.geo import area_contains

MAX_DEPTH = 10
# A cell crossed by at most this many edges is not split further.
LEAF_EDGES = 12

Bounds = tuple[float, float, float, float]  # west, south, east, north
Edge = tuple[float, float, float, float]  # x1, y1, x2, y2


class HasArea(Protocol):
    @property
    def area(self) -> Any: ...


T = TypeVar("T", bound=HasArea)


def _edges(area: dict[str, Any]) -> list[Edge]:
    polygons = [area["coordinates"]] if area["type"] == "Polygon" else area["coordinates"]
    return [
        (a[0], a[1], b[0], b[1])
        for polygon in polygons
        for ring in polygon
        for a, b in zip(ring, ring[1:])
    ]


def _crosses(edge: Edge, bounds: Bounds) -> bool:
    """Whether a segment touches a box (Liang-Barsky clipping)."""
    x1, y1, x2, y2 = edge
    west, south, east, north = bounds
    dx, dy = x2 - x1, y2 - y1
    low, high = 0.0, 1.0
    for p, q in ((-dx, x1 - west), (dx, east - x1), (-dy, y1 - south), (dy, north - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                low = max(low, t)
            else:
                high = min(high, t)
            if low > high:
                return False
    return True


def _point(x: float, y: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [x, y]}


class _Node(Generic[T]):
    __slots__ = ("bounds", "children", "entries")

    def __init__(self, bounds: Bounds) -> None:
        self.bounds = bounds
        self.children: list[_Node[T]] | None = None
        # Leaf: (item, exact) in priority order, where exact means "test the point".
        # Items not listed do not contain any point of the cell.
        self.entries: list[tuple[T, bool]] = []


class AreaQuadtree(Generic[T]):
    """Find the first item (in the given order) whose area contains a point."""

    def __init__(self, items: Sequence[T]) -> None:
        candidates = [(item, _edges(item.area)) for item in items if item.area]
        xs = [c for _, edges in candidates for e in edges for c in (e[0], e[2])]
        ys = [c for _, edges in candidates for e in edges for c in (e[1], e[3])]
        self.root: _Node[T] | None = None
        if xs:
            self.root = self._build((min(xs), min(ys), max(xs), max(ys)), candidates, 0)

    def _build(
        self, bounds: Bounds, candidates: list[tuple[T, list[Edge]]], depth: int
    ) -> _Node[T]:
        node: _Node[T] = _Node(bounds)
        west, south, east, north = bounds
        centre = _point((west + east) / 2, (south + north) / 2)

        crossing: list[tuple[T, list[Edge]]] = []
        for item, edges in candidates:
            inside_edges = [e for e in edges if _crosses(e, bounds)]
            if inside_edges:
                crossing.append((item, inside_edges))
                node.entries.append((item, True))
            elif area_contains(item.area, centre):
                # The whole cell is inside: lower-priority items can never win here.
                node.entries.append((item, False))
                break

        edge_count = sum(len(edges) for _, edges in crossing)
        if depth >= MAX_DEPTH or edge_count <= LEAF_EDGES:
            return node

        # Split. Items wholly containing the cell are passed down with no edges.
        passed = [(item, edges) for item, edges in crossing]
        if node.entries and not node.entries[-1][1]:
            passed.append((node.entries[-1][0], []))
        order = {id(item): i for i, (item, _) in enumerate(candidates)}
        passed.sort(key=lambda entry: order[id(entry[0])])

        mid_x, mid_y = (west + east) / 2, (south + north) / 2
        node.children = [
            self._build(quadrant, passed, depth + 1)
            for quadrant in (
                (west, south, mid_x, mid_y),
                (mid_x, south, east, mid_y),
                (west, mid_y, mid_x, north),
                (mid_x, mid_y, east, north),
            )
        ]
        node.entries = []
        return node

    def find(self, point: dict[str, Any] | None) -> T | None:
        if not point or point.get("type") != "Point" or self.root is None:
            return None
        x, y = point["coordinates"][:2]
        west, south, east, north = self.root.bounds
        if not (west <= x <= east and south <= y <= north):
            return None

        node = self.root
        while node.children is not None:
            west, south, east, north = node.bounds
            mid_x, mid_y = (west + east) / 2, (south + north) / 2
            node = node.children[(x >= mid_x) + 2 * (y >= mid_y)]

        for item, exact in node.entries:
            if not exact or area_contains(item.area, point):
                return item
        return None
