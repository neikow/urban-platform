"""Custom Wagtail user viewset wiring the role-aware forms and passing the
editing user (``for_user``) into them.
"""

from __future__ import annotations

from typing import Any

from wagtail.users.views.users import (
    CreateView as WagtailUserCreateView,
    EditView as WagtailUserEditView,
    UserViewSet as WagtailUserViewSet,
)

from .wagtail_forms import RoleUserCreationForm, RoleUserEditForm


class RoleUserCreateView(WagtailUserCreateView):
    def get_form_kwargs(self) -> dict[str, Any]:
        # Wagtail's user forms are plain ModelForms, so the generic view does
        # not inject ``for_user`` automatically; do it here.
        kwargs = super().get_form_kwargs()
        kwargs["for_user"] = self.request.user
        return kwargs


class RoleUserEditView(WagtailUserEditView):
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["for_user"] = self.request.user
        return kwargs


class UserViewSet(WagtailUserViewSet):
    add_view_class = RoleUserCreateView
    edit_view_class = RoleUserEditView

    def get_form_class(self, for_update: bool = False) -> type:
        return RoleUserEditForm if for_update else RoleUserCreationForm
