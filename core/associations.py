"""Attach users to the neighborhood association whose area contains their address.

A single user is matched on the spot (sign-up, profile). Matching everyone again
after an area changed is a Celery task (core.tasks.reassign_residents), queued
once the change is committed: it reads every located user.
"""

from typing import TYPE_CHECKING, Any

from django.db import transaction

from core.area_index import AreaQuadtree
from publications.geo import area_contains

if TYPE_CHECKING:
    from core.models import NeighborhoodAssociation, User

# Users read and written per database round trip by reassign_residents.
BATCH_SIZE = 1000


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


def set_address(user: "User", address: str, location: dict[str, Any] | None) -> None:
    """Change the user's address and location, and attach the matching association (not saved)."""
    user.address = address
    user.location = location
    user.association = association_at(location)


def reassign_residents() -> int:
    """Recompute every located user's association, after an area changed. Returns the changes."""
    from core.models import User

    index = area_index()
    changed: list[User] = []
    users = User.objects.filter(location__isnull=False).only("pk", "location", "association_id")
    for user in users.iterator(chunk_size=BATCH_SIZE):
        association = index.find(user.location)
        association_id = association.pk if association else None
        if user.association_id != association_id:
            user.association_id = association_id
            changed.append(user)
    User.objects.bulk_update(changed, ["association"], batch_size=BATCH_SIZE)
    return len(changed)


def queue_reassignment() -> None:
    """Match everyone again in the background, once the current transaction commits."""
    from core.tasks import reassign_residents as task

    transaction.on_commit(task.delay)  # type: ignore[attr-defined]  # Celery task


def on_association_saved(
    sender: Any, instance: "NeighborhoodAssociation", created: bool, **kwargs: Any
) -> None:
    """post_save receiver: only a new or redrawn area moves anyone."""
    if instance.area != instance.loaded_area or (created and instance.area):
        queue_reassignment()
    instance.loaded_area = instance.area


def on_association_deleted(sender: Any, instance: "NeighborhoodAssociation", **kwargs: Any) -> None:
    """post_delete receiver: its residents may lie in a neighbouring area too."""
    if instance.area:
        queue_reassignment()
