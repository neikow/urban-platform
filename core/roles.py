"""What each staff role may do, beyond the permissions in core.auth_backends.

Page and media rights live on Wagtail groups (page permissions are granted to
groups on the page tree, and the moderation workflow asks a group to review),
so each role puts the user in one of Wagtail's two groups:

- Editors: create and edit pages and media, then submit pages for moderation.
- Moderators: the same, plus publish, unpublish and lock pages, and review the
  pages submitted. Wagtail emails them each submission (see the workflow on
  the root page).

The groups follow the role: they are not edited by hand.
"""

from typing import TYPE_CHECKING

from django.contrib.auth.models import Group

from core.models import UserRole

if TYPE_CHECKING:
    from core.models import User

EDITORS_GROUP = "Editors"
MODERATORS_GROUP = "Moderators"
ROLE_GROUPS: dict[str, str] = {
    UserRole.EDITOR: EDITORS_GROUP,
    UserRole.MODERATOR: MODERATORS_GROUP,
    UserRole.ADMIN: MODERATORS_GROUP,
}
MANAGED_GROUPS = (EDITORS_GROUP, MODERATORS_GROUP)


def sync_role_groups(user: "User") -> None:
    """Put the user in the group of their role, and out of the other managed one."""
    wanted = ROLE_GROUPS.get(user.role) if user.is_active else None
    for group in Group.objects.filter(name__in=MANAGED_GROUPS):
        if group.name == wanted:
            user.groups.add(group)
        else:
            user.groups.remove(group)


def administrators(exclude: "User | None" = None) -> "list[User]":
    """Active accounts able to manage users: the administrators and superusers."""
    from django.db.models import Q

    from core.models import User

    users = User.objects.filter(Q(role=UserRole.ADMIN) | Q(is_superuser=True), is_active=True)
    if exclude is not None and exclude.pk:
        users = users.exclude(pk=exclude.pk)
    return list(users)


def is_last_administrator(user: "User") -> bool:
    """Whether removing this account's rights would leave nobody to manage users."""
    is_admin = user.is_active and (user.is_superuser or user.role == UserRole.ADMIN)
    return is_admin and not administrators(exclude=user)
