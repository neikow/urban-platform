from typing import Any

from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from core.models import Territory
from publications.views.mixins import ParticipationStatsPermissionMixin

from publications.models import ParticipationMode, ProjectPage
from publications.models.idea import IdeaResponse


def _local_postal_codes() -> list[str]:
    """The territory's postal codes: residents counted by default."""
    return Territory.current().postal_code_list


def _is_show_all(request: Any) -> bool:
    """Everyone is counted when asked, or when the territory has no postal codes."""
    return request.GET.get("show_all") == "1" or not _local_postal_codes()


def _local_ideas_filter() -> Q:
    """Return a Q filter for ideas from local users (the territory's postal codes)."""
    return Q(idea_responses__user__postal_code__in=_local_postal_codes())


def _local_responses_qs(show_all: bool) -> QuerySet:
    """Return an IdeaResponse queryset filtered by locality unless show_all is True."""
    qs = IdeaResponse.objects.all()
    if not show_all:
        qs = qs.filter(user__postal_code__in=_local_postal_codes())
    return qs


class IdeaStatsView(ParticipationStatsPermissionMixin, WagtailAdminTemplateMixin, TemplateView):
    template_name = "publications/admin/ideas_stats.html"
    page_title = _("Idea Collection")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        show_all = _is_show_all(self.request)
        local_filter = Q() if show_all else _local_ideas_filter()

        projects = (
            ProjectPage.objects.live()
            .filter(participation_mode=ParticipationMode.IDEAS)
            .annotate(total_ideas=Count("idea_responses", filter=local_filter))
            .order_by("-first_published_at")
        )

        projects_stats = [
            {
                "project": project,
                "total_ideas": project.total_ideas,
            }
            for project in projects
        ]

        context.update(
            {
                "projects_stats": projects_stats,
                "show_all": show_all,
                "local_postal_code": ", ".join(_local_postal_codes()),
            }
        )

        return context


class IdeaStatsDetailView(
    ParticipationStatsPermissionMixin, WagtailAdminTemplateMixin, TemplateView
):
    template_name = "publications/admin/ideas_stats_detail.html"
    page_title = _("Idea Collection")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        show_all = _is_show_all(self.request)
        project_id = self.kwargs.get("project_id")
        project = get_object_or_404(ProjectPage, id=project_id)

        ideas = (
            _local_responses_qs(show_all)
            .filter(project=project)
            .select_related("user")
            .order_by("-created_at")
        )

        context.update(
            {
                "project": project,
                "ideas": ideas,
                "total_ideas": ideas.count(),
                "show_all": show_all,
                "local_postal_code": ", ".join(_local_postal_codes()),
            }
        )

        return context
