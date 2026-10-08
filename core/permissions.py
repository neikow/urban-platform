"""Role-assignment permission rules for the Wagtail user admin.

Single source of truth for *which* roles a given editor may assign to other
users. Kept free of Django form/view imports so it stays trivially testable.
"""

from __future__ import annotations

from .models import User, UserRole


def assignable_roles(editor: User | None) -> list[str]:
    """Return the role values ``editor`` is allowed to assign to other users.

    Only administrators (and superusers) manage accounts, and they may assign
    every role, administrator included.
    """
    if editor is None or not editor.is_authenticated:
        return []
    if editor.has_role(UserRole.ADMIN):
        return list(UserRole.values)
    return []


def can_assign_role(editor: User | None, role: str) -> bool:
    """Whether ``editor`` is permitted to assign ``role`` to a user."""
    return role in assignable_roles(editor)


def can_change_role(editor: User | None, current_role: str | None, new_role: str) -> bool:
    """Whether ``editor`` may change a user's role from ``current_role`` to ``new_role``.

    Leaving the role unchanged is always allowed. Otherwise the editor must have
    authority over *both* roles.
    """
    if new_role == current_role:
        return True
    if current_role is not None and not can_assign_role(editor, current_role):
        return False
    return can_assign_role(editor, new_role)
