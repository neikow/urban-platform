"""Legal pages are edited by administrators only.

Changing the code of conduct asks every user to accept it again, and the other
pages are commitments of the association: editors and moderators may read them
in the admin, but not change them.
"""

from typing import Any

from wagtail.models import PagePermissionTester


class AdministratorsOnlyPermissionTester(PagePermissionTester):
    def __init__(self, user: Any, page: Any) -> None:
        super().__init__(user, page)
        is_admin = getattr(user, "has_role", lambda role: False)("ADMIN")
        if user.is_active and not user.is_superuser and not is_admin:
            self.permissions: set[str] = set()


class AdministratorsOnlyPageMixin:
    def permissions_for_user(self, user: Any) -> PagePermissionTester:
        return AdministratorsOnlyPermissionTester(user, self)
