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
from wagtail.admin.views.generic.models import CreateView

from core.models import Membership, User


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


class MembershipFilterSet(WagtailFilterSet):
    running = django_filters.BooleanFilter(
        label=_("Running today"), method="filter_running", widget=forms.NullBooleanSelect
    )

    class Meta:
        model = Membership
        fields = ["running"]

    def filter_running(self, queryset: Any, name: str, value: bool | None) -> Any:
        if value is None:
            return queryset
        active = Membership.objects.active().values("pk")
        return queryset.filter(pk__in=active) if value else queryset.exclude(pk__in=active)


class MembershipCreateView(CreateView):
    def get_initial(self) -> dict[str, Any]:
        # "Record a membership" on a user's page comes with ?user=<pk>.
        initial = super().get_initial()
        if user_id := self.request.GET.get("user"):
            initial["user"] = User.objects.filter(pk=user_id).first()
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
    list_display = ["user", "starts_on", "ends_on", "note"]
    list_export = ["user.get_full_name", "user.email", "starts_on", "ends_on", "note", "created_at"]
    export_headings = {"user.get_full_name": _("Member"), "user.email": _("Email")}
    export_filename = "adhesions"
    filterset_class = MembershipFilterSet
    search_fields = ["user__email", "user__first_name", "user__last_name", "note"]
    ordering = ["-starts_on"]

    def get_form_class(self, for_update: bool = False) -> Any:
        from wagtail.admin.forms import WagtailAdminModelForm

        class MembershipForm(WagtailAdminModelForm):
            class Meta:
                model = Membership
                fields = ["user", "starts_on", "ends_on", "note"]
                widgets = {"user": user_chooser_viewset.widget_class}

            def clean(self) -> dict[str, Any]:
                cleaned = super().clean() or {}
                starts, ends = cleaned.get("starts_on"), cleaned.get("ends_on")
                if starts and ends and ends < starts:
                    self.add_error("ends_on", _("The end cannot come before the start."))
                return cleaned

        return MembershipForm


membership_viewset = MembershipViewSet("membership")
