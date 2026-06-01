"""Custom Wagtail user create/edit forms that expose the ``role`` field and
enforce who is allowed to assign which role.
"""

from __future__ import annotations

from typing import Any, cast

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.users.forms import UserCreationForm, UserEditForm

from .models import UserRole
from .permissions import assignable_roles, can_change_role


class RoleRestrictionMixin(forms.ModelForm):
    """Restrict the ``role`` field to the roles the editing user may assign.

    The editing user is supplied via the ``for_user`` keyword argument, injected
    by the user viewset (see :mod:`core.wagtail_viewsets`).
    """

    for_user = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.for_user = kwargs.pop("for_user", None)
        super().__init__(*args, **kwargs)
        self._restrict_role_choices()

    def _restrict_role_choices(self) -> None:
        if "role" not in self.fields:
            return

        allowed = assignable_roles(self.for_user)

        # If the editor has no authority over the target's current role (e.g. an
        # ASSOCIATION_MEMBER editing an ADMIN), lock the field to that value so
        # the role cannot be changed and the select still renders correctly.
        current = getattr(self.instance, "role", None)
        if current is not None and current not in allowed:
            allowed = [current]

        labels = dict(UserRole.choices)
        role_field = cast("forms.ChoiceField", self.fields["role"])
        role_field.choices = [(value, labels[value]) for value in allowed]

    def clean_role(self) -> str:
        role: str = self.cleaned_data["role"]
        current = getattr(self.instance, "role", None)

        if not can_change_role(self.for_user, current, role):
            raise forms.ValidationError(
                _("You do not have permission to assign this role."),
                code="role_not_allowed",
            )
        return role


class RoleUserCreationForm(RoleRestrictionMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields | {"role"}


class RoleUserEditForm(RoleRestrictionMixin, UserEditForm):
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields | {"role"}
