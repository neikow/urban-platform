"""Authentication backend that derives Wagtail permissions from the user role.

This replaces the deprecated ``is_staff`` flag: rather than storing a separate
boolean, a user's :class:`~core.models.user.UserRole` decides what they may do
in the Wagtail admin. Each role in :data:`ROLE_PERMISSIONS` is granted a fixed
set of Django permissions on top of any stored in the database:

- ``wagtailadmin.access_admin`` lets a user enter the Wagtail admin at all (the
  permission Wagtail's ``require_admin_access`` checks, see ``wagtail.admin.auth``).
- Editors: the admin only. Their page and media rights come from the Wagtail
  group of their role (core.roles).
- Moderators: also the announcement and the vote and idea statistics.
- Administrators: also the users and the website settings (associations, map,
  features, tasks).
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

# Settings > Announcement: the band shown at the top of every page.
ANNOUNCEMENT_PERMISSIONS: frozenset[str] = frozenset({"core.change_announcement"})

# Vote and idea statistics hold personal data.
PARTICIPATION_STATS_PERMISSIONS: frozenset[str] = frozenset({"core.view_participation_stats"})

# Website settings: neighborhood associations, map, features, tasks, email log.
SITE_SETTINGS_PERMISSIONS: frozenset[str] = frozenset(
    {
        "core.add_neighborhoodassociation",
        "core.change_neighborhoodassociation",
        "core.delete_neighborhoodassociation",
        "core.view_neighborhoodassociation",
        "core.change_featureflags",
        "core.view_emailevent",
        "core.manage_tasks",
        "core.view_taskrun",
        "core.view_audit_log",
        "publications.change_mapsettings",
    }
)

# Roles that may access the Wagtail admin. Kept for backwards compatibility; it
# is now derived from :data:`ROLE_PERMISSIONS`.
ADMIN_ACCESS_ROLES: frozenset[str] = frozenset(
    {UserRole.EDITOR, UserRole.MODERATOR, UserRole.ADMIN}
)

# Permissions granted purely from a user's role, on top of database-stored ones.
# Page and media rights come from the Wagtail group of the role (core.roles).
_EDITOR = frozenset({WAGTAIL_ADMIN_PERMISSION})
_MODERATOR = _EDITOR | ANNOUNCEMENT_PERMISSIONS | PARTICIPATION_STATS_PERMISSIONS
_ADMIN = _MODERATOR | USER_MANAGEMENT_PERMISSIONS | SITE_SETTINGS_PERMISSIONS
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    UserRole.EDITOR: _EDITOR,
    UserRole.MODERATOR: _MODERATOR,
    UserRole.ADMIN: _ADMIN,
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
