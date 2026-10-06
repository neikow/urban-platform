from collections.abc import Iterable

from django.db.models import QuerySet

from core.models import User
from core.notifications import NotificationKind


def opted_in(kind: NotificationKind, user_ids: Iterable[int]) -> QuerySet[User]:
    """Active, verified users among `user_ids` who asked for this kind of email."""
    return User.objects.filter(
        pk__in=list(user_ids),
        is_active=True,
        is_verified=True,
        **{kind.preference_field: True},
    )
