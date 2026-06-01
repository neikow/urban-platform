"""Authentication backend that derives Wagtail admin access from the user role.

This replaces the deprecated ``is_staff`` flag: rather than storing a separate
boolean, a user's :class:`~core.models.user.UserRole` decides whether they may
enter the Wagtail admin. Roles in :data:`ADMIN_ACCESS_ROLES` are granted the
``wagtailadmin.access_admin`` permission, which is the permission Wagtail's
``require_admin_access`` checks (see ``wagtail.admin.auth``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.backends import ModelBackend

from .models import UserRole

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import Model

    from .models import User

# Roles that may access the Wagtail admin.
ADMIN_ACCESS_ROLES: frozenset[str] = frozenset({UserRole.ADMIN, UserRole.ASSOCIATION_MEMBER})

WAGTAIL_ADMIN_PERMISSION = "wagtailadmin.access_admin"


class RolePermissionsBackend(ModelBackend):
    """Standard ``ModelBackend`` plus role-derived Wagtail admin access."""

    def get_all_permissions(
        self, user_obj: "User | AnonymousUser", obj: "Model | None" = None
    ) -> set[str]:
        perms = super().get_all_permissions(user_obj, obj)
        if (
            obj is None
            and user_obj.is_active
            and not user_obj.is_anonymous
            and getattr(user_obj, "role", None) in ADMIN_ACCESS_ROLES
        ):
            return perms | {WAGTAIL_ADMIN_PERMISSION}
        return perms
