"""Attach users to a neighborhood association (CIQ).

A user may choose their association. Otherwise they follow their address: the
association whose area contains it, or else the one whose seat is nearest.

A single user is matched on the spot (sign-up, profile). Matching everyone again
after an area or a seat moved is a Celery task (core.tasks.reassign_residents),
queued once the change is committed: it reads every located user who did not
choose.
"""

import math
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from django.db import transaction

from core.area_index import AreaQuadtree
from publications.geo import area_contains

if TYPE_CHECKING:
    from core.models import NeighborhoodAssociation, User

# Users read and written per database round trip by reassign_residents.
BATCH_SIZE = 1000
EARTH_RADIUS_METERS = 6_371_000


def distance_meters(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Great-circle distance between two GeoJSON points."""
    (lon1, lat1), (lon2, lat2) = a["coordinates"][:2], b["coordinates"][:2]
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi, d_lambda = phi2 - phi1, math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(h))


def area_index() -> "AreaQuadtree[NeighborhoodAssociation]":
    """The associations' areas, indexed for point lookups (first by name wins)."""
    from core.models import NeighborhoodAssociation

    return AreaQuadtree(list(NeighborhoodAssociation.objects.filter(area__isnull=False)))


def association_at(point: dict[str, Any] | None) -> "NeighborhoodAssociation | None":
    """The first association (by name) whose area contains the point.

    A plain scan: for a single point, building the quadtree would cost more.
    """
    from core.models import NeighborhoodAssociation

    if not point:
        return None
    associations = NeighborhoodAssociation.objects.filter(area__isnull=False)
    return next((a for a in associations if area_contains(a.area, point)), None)


def nearest_seat(
    point: dict[str, Any], associations: Iterable["NeighborhoodAssociation"]
) -> "NeighborhoodAssociation | None":
    """The association whose located seat (address) is nearest to the point."""
    seats = [(a, a.address_location) for a in associations if a.address_location]
    nearest = min(seats, key=lambda seat: distance_meters(point, seat[1]), default=None)
    return nearest[0] if nearest else None


def nearest_association(point: dict[str, Any] | None) -> "NeighborhoodAssociation | None":
    """The association a resident living at the point belongs to, if they do not choose."""
    from core.models import NeighborhoodAssociation

    if not point:
        return None
    return association_at(point) or nearest_seat(point, NeighborhoodAssociation.objects.all())


def ranked_associations(
    point: dict[str, Any] | None,
) -> list[tuple["NeighborhoodAssociation", float | None]]:
    """Every association with its distance to the point, nearest first.

    An association whose area contains the point comes first, at distance 0.
    Associations without a located seat come last, by name, with no distance.
    """
    from core.models import NeighborhoodAssociation

    associations = list(NeighborhoodAssociation.objects.all())
    if not point:
        return [(a, None) for a in associations]
    containing = association_at(point)

    def distance(association: "NeighborhoodAssociation") -> float | None:
        if association == containing:
            return 0.0
        if association.address_location:
            return distance_meters(point, association.address_location)
        return None

    ranked = [(a, distance(a)) for a in associations]
    return sorted(ranked, key=lambda item: (item[1] is None, item[1] or 0))


def attach_association(user: "User", choice: "NeighborhoodAssociation | None" = None) -> None:
    """Attach the user to their choice, or to the association of their address (not saved).

    Choosing the association their address leads to anyway is not a choice: they
    keep following their address.
    """
    nearest = nearest_association(user.location)
    if choice is not None and choice != nearest:
        user.association, user.association_chosen = choice, True
    else:
        user.association, user.association_chosen = nearest, False


def set_address(
    user: "User",
    address: str,
    location: dict[str, Any] | None,
    choice: "NeighborhoodAssociation | None" = None,
) -> None:
    """Change the user's address and location, and attach their association (not saved)."""
    user.address = address
    user.location = location
    attach_association(user, choice)


def reassign_residents() -> int:
    """Recompute the association of every located user who did not choose. Returns the changes."""
    from core.models import NeighborhoodAssociation, User

    index = area_index()
    seats = list(NeighborhoodAssociation.objects.filter(address_location__isnull=False))
    changed: list[User] = []
    users = User.objects.filter(location__isnull=False, association_chosen=False).only(
        "pk", "location", "association_id"
    )
    for user in users.iterator(chunk_size=BATCH_SIZE):
        location: dict[str, Any] = user.location  # type: ignore[assignment]  # filtered not null
        association = index.find(location) or nearest_seat(location, seats)
        association_id = association.pk if association else None
        if user.association_id != association_id:
            user.association_id = association_id
            changed.append(user)
    User.objects.bulk_update(changed, ["association"], batch_size=BATCH_SIZE)
    return len(changed)


# While set, reassignments are only noted (see paused_reassignment).
_paused: ContextVar[list[bool] | None] = ContextVar("reassignment_paused", default=None)


@contextmanager
def paused_reassignment() -> Iterator[None]:
    """Queue a single reassignment for all the association changes made inside the block."""
    requests: list[bool] = []
    token = _paused.set(requests)
    try:
        yield
    finally:
        _paused.reset(token)
    if requests:
        queue_reassignment()


def queue_reassignment() -> None:
    """Match everyone again in the background, once the current transaction commits."""
    from core.tasks import reassign_residents as task

    requests = _paused.get()
    if requests is not None:
        requests.append(True)
        return
    transaction.on_commit(task.delay)  # type: ignore[attr-defined]  # Celery task


def on_association_saved(
    sender: Any, instance: "NeighborhoodAssociation", created: bool, **kwargs: Any
) -> None:
    """post_save receiver: only a new or moved area or seat moves anyone."""
    moved = (
        instance.area != instance.loaded_area
        or instance.address_location != instance.loaded_address_location
    )
    if moved or (created and (instance.area or instance.address_location)):
        queue_reassignment()
    instance.loaded_area = instance.area
    instance.loaded_address_location = instance.address_location


def on_association_deleted(sender: Any, instance: "NeighborhoodAssociation", **kwargs: Any) -> None:
    """post_delete receiver: its residents may lie in a neighbouring area, or near another seat."""
    from core.models import User

    # Those who had chosen it follow their address again.
    orphans = User.objects.filter(association_chosen=True, association__isnull=True)
    if orphans.update(association_chosen=False) or instance.area or instance.address_location:
        queue_reassignment()
