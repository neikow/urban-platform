from typing import Any

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from publications.models import ProjectPage
from publications.models.form import (
    FAVORABLE_VALUES,
    FormResponse,
    UNFAVORABLE_VALUES,
    VoteChoice,
)


class VoteStatsView(WagtailAdminTemplateMixin, TemplateView):
    template_name = "publications/admin/vote_stats.html"
    page_title = _("Vote Statistics")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        projects = (
            ProjectPage.objects.live()
            .filter(enable_voting=True)
            .annotate(
                total_votes=Count("vote_responses"),
                with_comments=Count(
                    "vote_responses",
                    filter=Q(vote_responses__comment__isnull=False)
                    & ~Q(vote_responses__comment=""),
                ),
                favorable_count=Count(
                    "vote_responses",
                    filter=Q(vote_responses__choice__in=FAVORABLE_VALUES),
                ),
            )
            .order_by("-first_published_at")
        )

        projects_stats = [
            {
                "project": project,
                "total_votes": project.total_votes,
                "with_comments": project.with_comments,
                "favorable_percent": (
                    round((project.favorable_count / project.total_votes) * 100, 1)
                    if project.total_votes > 0
                    else 0
                ),
                "is_voting_open": project.is_voting_open,
            }
            for project in projects
        ]

        context.update(
            {
                "projects_stats": projects_stats,
            }
        )

        return context


class VoteStatsDetailView(WagtailAdminTemplateMixin, TemplateView):
    template_name = "publications/admin/vote_stats_detail.html"
    page_title = _("Vote Statistics")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        project_id = self.kwargs.get("project_id")
        project = get_object_or_404(ProjectPage, id=project_id)

        vote_counts = (
            FormResponse.objects.filter(project=project)
            .values("choice")
            .annotate(
                count=Count("id"),
                with_comment=Count("id", filter=Q(comment__isnull=False) & ~Q(comment="")),
            )
        )

        counts = {choice.value: 0 for choice in VoteChoice}
        counts_with_comment = {choice.value: 0 for choice in VoteChoice}
        total = 0
        for vc in vote_counts:
            counts[vc["choice"]] = vc["count"]
            counts_with_comment[vc["choice"]] = vc["with_comment"]
            total += vc["count"]

        percentages = {}
        for choice in VoteChoice:
            if total > 0:
                percentages[choice.value] = round((counts[choice.value] / total) * 100, 1)
            else:
                percentages[choice.value] = 0

        favorable_total = sum(counts[choice] for choice in FAVORABLE_VALUES)
        unfavorable_total = sum(counts[choice] for choice in UNFAVORABLE_VALUES)
        favorable_percentage = round((favorable_total / total) * 100, 1) if total > 0 else 0
        unfavorable_percentage = round((unfavorable_total / total) * 100, 1) if total > 0 else 0

        votes_with_comments = (
            FormResponse.objects.filter(project=project)
            .exclude(comment="")
            .exclude(comment__isnull=True)
            .select_related("user")
            .order_by("-created_at")
        )

        context.update(
            {
                "project": project,
                "total_votes": total,
                "counts": counts,
                "counts_with_comment": counts_with_comment,
                "percentages": percentages,
                "favorable_total": favorable_total,
                "favorable_percentage": favorable_percentage,
                "unfavorable_total": unfavorable_total,
                "unfavorable_percentage": unfavorable_percentage,
                "is_voting_open": project.is_voting_open,
                "votes_with_comments": votes_with_comments,
                "vote_choices": VoteChoice,
            }
        )

        return context
