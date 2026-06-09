"""Authentication backend that derives Wagtail permissions from the user role.

This replaces the deprecated ``is_staff`` flag: rather than storing a separate
boolean, a user's :class:`~core.models.user.UserRole` decides what they may do
in the Wagtail admin. Each role in :data:`ROLE_PERMISSIONS` is granted a fixed
set of Django permissions on top of any stored in the database:

- ``wagtailadmin.access_admin`` lets a user enter the Wagtail admin at all (the
  permission Wagtail's ``require_admin_access`` checks, see ``wagtail.admin.auth``).
- The ``core.*_user`` permissions in :data:`USER_MANAGEMENT_PERMISSIONS` unlock
  the Wagtail user admin at ``/admin/users/``. *Which* roles such a user may then
  assign is further constrained by :mod:`core.permissions`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.backends import ModelBackend

from .models import UserRole

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import Model

    from .models import User

WAGTAIL_ADMIN_PERMISSION = "wagtailadmin.access_admin"

# Permissions Wagtail's user admin (``/admin/users/``) checks. Granting any of
# them makes the "Utilisateurs" view reachable; add/change/delete also enable the
# matching actions there.
USER_MANAGEMENT_PERMISSIONS: frozenset[str] = frozenset(
    {
        "core.add_user",
        "core.change_user",
        "core.delete_user",
        "core.view_user",
    }
)

# Roles that may access the Wagtail admin. Kept for backwards compatibility; it
# is now derived from :data:`ROLE_PERMISSIONS`.
ADMIN_ACCESS_ROLES: frozenset[str] = frozenset({UserRole.ADMIN, UserRole.ASSOCIATION_MEMBER})

# Permissions granted purely from a user's role, on top of database-stored ones.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    UserRole.ADMIN: frozenset({WAGTAIL_ADMIN_PERMISSION}) | USER_MANAGEMENT_PERMISSIONS,
    UserRole.ASSOCIATION_MEMBER: frozenset({WAGTAIL_ADMIN_PERMISSION})
    | USER_MANAGEMENT_PERMISSIONS,
}


class RolePermissionsBackend(ModelBackend):
    """Standard ``ModelBackend`` plus role-derived Wagtail permissions."""

    def get_all_permissions(
        self, user_obj: "User | AnonymousUser", obj: "Model | None" = None
    ) -> set[str]:
        perms = super().get_all_permissions(user_obj, obj)
        if obj is not None or user_obj.is_anonymous or not user_obj.is_active:
            return perms
        role: str | None = getattr(user_obj, "role", None)
        if role is None:
            return perms
        return perms | ROLE_PERMISSIONS.get(role, frozenset())
