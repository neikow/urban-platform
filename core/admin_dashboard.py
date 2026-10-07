"""Panels at the top of the admin dashboard.

What an editor needs on arrival: shortcuts to the frequent tasks, the
consultations and events to keep an eye on, and the drafts not published
yet. Added by the ``construct_homepage_panels`` hook in ``core.wagtail_hooks``;
their ``order`` puts them before Wagtail's own panels (110 and up).
"""

from typing import Any

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui.components import Component
from wagtail.models import Page
from wagtail.permission_policies.pages import PagePermissionPolicy

DRAFTS_SHOWN = 10
EVENTS_SHOWN = 5


class DashboardPanel(Component):
    def get_context_data(self, parent_context: Any = None) -> dict[str, Any]:
        context = super().get_context_data(parent_context)
        context["request"] = parent_context["request"]
        return context


class QuickActionsPanel(DashboardPanel):
    name = "quick_actions"
    order = 10
    template_name = "core/admin/dashboard/quick_actions.html"

    def get_context_data(self, parent_context: Any = None) -> dict[str, Any]:
        from home.models import HomePage
        from pedagogy.models import PedagogyCardPage, PedagogyIndexPage
        from publications.models import EventPage, ProjectPage, PublicationIndexPage

        context = super().get_context_data(parent_context)
        user = context["request"].user
        actions = []

        def add_page(label: Any, parent: Page | None, page_class: type[Page]) -> None:
            if parent and parent.permissions_for_user(user).can_add_subpage():
                url = reverse(
                    "wagtailadmin_pages:add",
                    args=[page_class._meta.app_label, page_class._meta.model_name, parent.pk],
                )
                actions.append({"label": label, "url": url, "icon": "plus"})

        news = PublicationIndexPage.objects.first()
        add_page(_("New project"), news, ProjectPage)
        add_page(_("New event"), news, EventPage)
        add_page(
            _("New “Useful information” card"), PedagogyIndexPage.objects.first(), PedagogyCardPage
        )

        home = HomePage.objects.first()
        if home and home.permissions_for_user(user).can_edit():
            actions.append(
                {
                    "label": _("Edit the home page"),
                    "url": reverse("wagtailadmin_pages:edit", args=[home.pk]),
                    "icon": "home",
                }
            )
        if user.has_perm("core.change_announcement"):
            actions.append(
                {
                    "label": _("Edit the announcement"),
                    "url": reverse("wagtailsettings:edit", args=["core", "announcement"]),
                    "icon": "info-circle",
                }
            )
        context["actions"] = actions
        return context


class ConsultationsPanel(DashboardPanel):
    name = "consultations"
    order = 20
    template_name = "core/admin/dashboard/consultations.html"

    def get_context_data(self, parent_context: Any = None) -> dict[str, Any]:
        from home.blocks import open_projects
        from publications.models import ProjectPage

        context = super().get_context_data(parent_context)
        projects = open_projects()
        counts = ProjectPage.objects.filter(pk__in=[p.pk for p in projects]).annotate(
            votes=Count("vote_responses", distinct=True),
            ideas=Count("idea_responses", distinct=True),
        )
        responses = {p.pk: (p.votes, p.ideas) for p in counts}
        context["consultations"] = [
            {
                "project": project,
                "is_vote": project.is_voting_open,
                "responses": responses[project.pk][0 if project.is_voting_open else 1],
                "results_url": reverse(
                    "vote_statistics_detail"
                    if project.is_voting_open
                    else "idea_statistics_detail",
                    args=[project.pk],
                ),
            }
            for project in projects
        ]
        return context


class UpcomingEventsPanel(DashboardPanel):
    name = "upcoming_events"
    order = 30
    template_name = "core/admin/dashboard/upcoming_events.html"

    def get_context_data(self, parent_context: Any = None) -> dict[str, Any]:
        from publications.models import EventPage

        context = super().get_context_data(parent_context)
        now = timezone.now()
        context["events"] = (
            EventPage.objects.live()
            .filter(Q(event_date__gte=now) | Q(end_date__gte=now))
            .annotate(interested=Count("interests"))
            .order_by("event_date")[:EVENTS_SHOWN]
        )
        return context


class DraftsPanel(DashboardPanel):
    """Pages with changes not published yet, by anyone, that the user may edit."""

    name = "drafts"
    order = 40
    template_name = "core/admin/dashboard/drafts.html"

    def get_context_data(self, parent_context: Any = None) -> dict[str, Any]:
        context = super().get_context_data(parent_context)
        editable = PagePermissionPolicy().instances_user_has_any_permission_for(
            context["request"].user, ["change"]
        )
        context["drafts"] = (
            editable.filter(has_unpublished_changes=True)
            .select_related("latest_revision__user")
            .order_by("-latest_revision_created_at")[:DRAFTS_SHOWN]
        )
        return context


def dashboard_panels() -> list[Component]:
    return [QuickActionsPanel(), ConsultationsPanel(), UpcomingEventsPanel(), DraftsPanel()]
