"""Attach users to the neighborhood association whose area contains their address."""

from typing import TYPE_CHECKING, Any

from publications.geo import area_contains

if TYPE_CHECKING:
    from core.models import NeighborhoodAssociation, User


def association_at(
    point: dict[str, Any] | None, associations: "list[NeighborhoodAssociation] | None" = None
) -> "NeighborhoodAssociation | None":
    """The first association (by name) whose area contains the point."""
    from core.models import NeighborhoodAssociation

    if not point:
        return None
    if associations is None:
        associations = list(NeighborhoodAssociation.objects.filter(area__isnull=False))
    return next((a for a in associations if area_contains(a.area, point)), None)


def set_address(user: "User", address: str, location: dict[str, Any] | None) -> None:
    """Change the user's address and location, and attach the matching association (not saved)."""
    user.address = address
    user.location = location
    user.association = association_at(location)


def reassign_residents() -> int:
    """Recompute every located user's association, after an area changed. Returns the changes."""
    from core.models import NeighborhoodAssociation, User

    associations = list(NeighborhoodAssociation.objects.filter(area__isnull=False))
    changed = []
    for user in User.objects.filter(location__isnull=False).only(
        "pk", "location", "association_id"
    ):
        association = association_at(user.location, associations)
        association_id = association.pk if association else None
        if user.association_id != association_id:
            user.association_id = association_id
            changed.append(user)
    User.objects.bulk_update(changed, ["association"])
    return len(changed)


def reassign_residents_on_change(sender: Any, **kwargs: Any) -> None:
    """post_save / post_delete receiver for NeighborhoodAssociation."""
    reassign_residents()
