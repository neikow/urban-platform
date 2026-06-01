"""Role-assignment permission rules for the Wagtail user admin.

Single source of truth for *which* roles a given editor may assign to other
users. Kept free of Django form/view imports so it stays trivially testable.
"""

from __future__ import annotations

from .models import User, UserRole

# Roles in their canonical declaration order, used to keep choice ordering stable.
_ROLE_ORDER: tuple[str, ...] = (
    UserRole.CITIZEN,
    UserRole.ASSOCIATION_MEMBER,
    UserRole.ADMIN,
)


def assignable_roles(editor: User | None) -> list[str]:
    """Return the role values ``editor`` is allowed to assign to other users.

    - Superusers and ``ADMIN`` users may assign any role (including ``ADMIN``).
    - ``ASSOCIATION_MEMBER`` users may assign only ``CITIZEN`` or
      ``ASSOCIATION_MEMBER``.
    - Anyone else may assign nothing.
    """
    if editor is None or not editor.is_authenticated:
        return []

    if editor.is_superuser or editor.role == UserRole.ADMIN:
        return list(_ROLE_ORDER)

    if editor.role == UserRole.ASSOCIATION_MEMBER:
        return [UserRole.CITIZEN, UserRole.ASSOCIATION_MEMBER]

    return []


def can_assign_role(editor: User | None, role: str) -> bool:
    """Whether ``editor`` is permitted to assign ``role`` to a user."""
    return role in assignable_roles(editor)


def can_change_role(editor: User | None, current_role: str | None, new_role: str) -> bool:
    """Whether ``editor`` may change a user's role from ``current_role`` to ``new_role``.

    Leaving the role unchanged is always allowed. Otherwise the editor must have
    authority over *both* roles, which notably prevents an ``ASSOCIATION_MEMBER``
    from demoting an existing ``ADMIN`` (they cannot assign ``ADMIN``, so they
    have no authority over admin users).
    """
    if new_role == current_role:
        return True
    if current_role is not None and not can_assign_role(editor, current_role):
        return False
    return can_assign_role(editor, new_role)
