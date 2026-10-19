"""Settings › Memberships: who is a member, since when, until when (core.models.Membership)."""

from typing import Any

import django_filters
from django import forms
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.forms.choosers import BaseFilterForm
from wagtail.admin.views.generic import chooser as chooser_views
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.views.generic.models import CreateView, IndexView
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.permissions import register_permission_policy

from core.models import Membership, MembershipPayment, User
from core.models.membership import MembershipQuerySet


# --- user chooser -------------------------------------------------------------------


class UserSearchForm(BaseFilterForm):
    """Users are not in the search index: search the database instead."""

    q = forms.CharField(
        label=_("Search term"),
        widget=forms.TextInput(attrs={"placeholder": _("Name or email")}),
        required=False,
    )

    def filter(self, objects: QuerySet[User]) -> QuerySet[User]:
        query = self.cleaned_data.get("q")
        if query:
            self.is_searching = True
            self.search_query = query
            objects = objects.filter(
                Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        return objects


class UserChooseView(chooser_views.ChooseView):
    filter_form_class = UserSearchForm


class UserChooseResultsView(chooser_views.ChooseResultsView):
    filter_form_class = UserSearchForm


class UserChooserViewSet(ChooserViewSet):
    model = User
    icon = "user"
    choose_one_text = _("Choose a user")
    choose_another_text = _("Choose another user")
    choose_view_class = UserChooseView
    choose_results_view_class = UserChooseResultsView
    register_widget = False  # only the membership form uses it


user_chooser_viewset = UserChooserViewSet("user_chooser")


# --- memberships ----------------------------------------------------------------------


def visible_memberships(user: Any, memberships: MembershipQuerySet) -> MembershipQuerySet:
    """All of them for administrators; those of their CIQ for a CIQ's responsible."""
    if user.has_perm("core.change_membership"):
        return memberships
    return memberships.filter(association__responsible=user)


class MembershipFilterSet(WagtailFilterSet):
    running = django_filters.BooleanFilter(
        label=_("Running today"), method="filter_running", widget=forms.NullBooleanSelect
    )
    year = django_filters.NumberFilter(label=_("Year"), method="filter_year")

    class Meta:
        model = Membership
        fields = ["running", "year", "association"]

    def filter_year(self, queryset: Any, name: str, value: Any) -> Any:
        """Memberships covering at least a day of the year."""
        if not value:
            return queryset
        year = int(value)
        return queryset.filter(starts_on__year__lte=year).filter(
            Q(ends_on__isnull=True) | Q(ends_on__year__gte=year)
        )

    def filter_running(self, queryset: Any, name: str, value: bool | None) -> Any:
        if value is None:
            return queryset
        active = Membership.objects.active().values("pk")
        return queryset.filter(pk__in=active) if value else queryset.exclude(pk__in=active)


class MembershipIndexView(IndexView):
    def get_base_queryset(self) -> MembershipQuerySet:
        return visible_memberships(self.request.user, super().get_base_queryset())


class MembershipCreateView(CreateView):
    def get_initial(self) -> dict[str, Any]:
        # "Record a membership" on a user's page comes with ?user=<pk>.
        initial = super().get_initial()
        if user_id := self.request.GET.get("user"):
            initial["user"] = user = User.objects.filter(pk=user_id).first()
            initial["association"] = user.association if user else None
        return initial

    def save_instance(self) -> Membership:
        self.form.instance.created_by = self.request.user
        return super().save_instance()


class MembershipViewSet(ModelViewSet):
    model = Membership
    icon = "group"
    menu_label = _("Memberships")
    add_to_settings_menu = True
    menu_order = 450
    add_view_class = MembershipCreateView
    index_view_class = MembershipIndexView
    list_display = ["user", "association", "starts_on", "ends_on", "note"]
    list_export = [
        "user.get_full_name",
        "user.email",
        "association",
        "starts_on",
        "ends_on",
        "note",
        "created_at",
    ]
    export_headings = {
        "user.get_full_name": _("Member"),
        "user.email": _("Email"),
        "association": _("Neighborhood Association"),
    }
    export_filename = "adhesions"
    filterset_class = MembershipFilterSet
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "association__name",
        "note",
    ]
    ordering = ["-starts_on"]

    def get_form_class(self, for_update: bool = False) -> Any:
        from wagtail.admin.forms import WagtailAdminModelForm

        class MembershipForm(WagtailAdminModelForm):
            class Meta:
                model = Membership
                fields = ["user", "association", "starts_on", "ends_on", "note"]
                widgets = {"user": user_chooser_viewset.widget_class}

            def clean(self) -> dict[str, Any]:
                cleaned = super().clean() or {}
                starts, ends = cleaned.get("starts_on"), cleaned.get("ends_on")
                if starts and ends and ends < starts:
                    self.add_error("ends_on", _("The end cannot come before the start."))
                return cleaned

        return MembershipForm


membership_viewset = MembershipViewSet("membership")


# --- payments (core.membership_payments) -----------------------------------------


class MembershipPaymentFilterSet(WagtailFilterSet):
    class Meta:
        model = MembershipPayment
        fields = ["status", "association"]


class ReadOnlyPermissionPolicy(ModelPermissionPolicy):
    """View permission only: no adding, editing or deleting from the admin."""

    def user_has_permission(self, user: Any, action: str) -> bool:
        return action not in ("add", "change", "delete") and super().user_has_permission(
            user, action
        )

    def user_has_any_permission(self, user: Any, actions: Any) -> bool:
        return any(self.user_has_permission(user, action) for action in actions)


class MembershipPaymentViewSet(ModelViewSet):
    """The memberships paid on HelloAsso: read only, they come from HelloAsso."""

    model = MembershipPayment
    icon = "doc-full"
    menu_label = _("Membership payments")
    add_to_settings_menu = True
    menu_order = 455
    inspect_view_enabled = True
    list_display = ["user", "association", "amount", "status", "ends_on", "order_id", "created_at"]
    list_export = [
        "user.get_full_name",
        "user.email",
        "association",
        "amount",
        "status",
        "starts_on",
        "ends_on",
        "order_id",
        "created_at",
        "paid_at",
    ]
    export_headings = {
        "user.get_full_name": _("Member"),
        "user.email": _("Email"),
        "association": _("Neighborhood Association"),
        "amount": _("Amount (€)"),
    }
    export_filename = "paiements-adhesions"
    filterset_class = MembershipPaymentFilterSet
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    ordering = ["-created_at"]
    form_fields = ["status"]


register_permission_policy(MembershipPayment, ReadOnlyPermissionPolicy(MembershipPayment))
membership_payment_viewset = MembershipPaymentViewSet("membership_payment")
