from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from publications.views.vote_stats import VoteStatsView, VoteStatsDetailView


@hooks.register("register_admin_urls")
def register_vote_stats_url() -> list[URLPattern]:
    return [
        path("vote-statistics/", VoteStatsView.as_view(), name="vote_statistics"),
        path(
            "vote-statistics/<int:project_id>/",
            VoteStatsDetailView.as_view(),
            name="vote_statistics_detail",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_vote_stats_menu_item() -> MenuItem:
    return MenuItem(
        _("Vote Statistics"),
        reverse("vote_statistics"),
        icon_name="success",
        order=202,
    )
