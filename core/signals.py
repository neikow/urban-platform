from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import User, UserRole

PRIVILEGED_GROUP_NAMES = frozenset({"Moderators", "Editors"})


def _sync_role_for_user(user: User) -> None:
    """Set role to ASSOCIATION_MEMBER if in a privileged group, else revert to CITIZEN.

    ADMIN users are never downgraded.
    """
    if user.role == UserRole.ADMIN:
        return

    has_privileged_group = user.groups.filter(name__in=PRIVILEGED_GROUP_NAMES).exists()
    new_role = UserRole.ASSOCIATION_MEMBER if has_privileged_group else UserRole.CITIZEN
    User.objects.filter(pk=user.pk).update(role=new_role)


@receiver(m2m_changed, sender=User.groups.through)
def sync_role_with_groups(
    sender: type, instance: User | Group, action: str, pk_set: set | None, **kwargs: object
) -> None:
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    if isinstance(instance, User):
        _sync_role_for_user(instance)
    else:
        # instance is a Group; pk_set contains User PKs (None on post_clear)
        if pk_set is not None:
            for user in User.objects.filter(pk__in=pk_set):
                _sync_role_for_user(user)
