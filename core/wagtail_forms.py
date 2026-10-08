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
from .roles import is_last_administrator, sync_role_groups


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
        if "groups" in self.fields:
            # Page and media rights follow the role (core.roles).
            self.fields["groups"].disabled = True
            self.fields["groups"].required = False
            self.fields["groups"].help_text = _("Set by the role.")

    def _restrict_role_choices(self) -> None:
        if "role" not in self.fields:
            return

        allowed = assignable_roles(self.for_user)

        # If the editor has no authority over the target's current role (e.g. an
        # editor with no user rights reaching the form), lock the field to that value so
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

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        instance = self.instance
        if instance.pk and is_last_administrator(type(instance).objects.get(pk=instance.pk)):
            demoted = cleaned_data.get("role", instance.role) != UserRole.ADMIN
            demoted = demoted and not cleaned_data.get("is_superuser", instance.is_superuser)
            if demoted or cleaned_data.get("is_active", True) is False:
                raise forms.ValidationError(
                    _("This is the last administrator: name another one first."),
                    code="last_administrator",
                )
        return cleaned_data

    def _save_m2m(self) -> None:
        super()._save_m2m()  # type: ignore[misc]
        sync_role_groups(self.instance)


class RoleUserCreationForm(RoleRestrictionMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields | {"role"}


class RoleUserEditForm(RoleRestrictionMixin, UserEditForm):
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields | {"role"}
