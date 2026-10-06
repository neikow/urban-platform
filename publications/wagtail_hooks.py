from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.widgets import Button

from publications.views.idea_stats import IdeaStatsView, IdeaStatsDetailView
from publications.views.poll_close import ClosePollView
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


@hooks.register("register_admin_urls")
def register_idea_stats_url() -> list[URLPattern]:
    return [
        path("idea-collection/", IdeaStatsView.as_view(), name="idea_statistics"),
        path(
            "idea-collection/<int:project_id>/",
            IdeaStatsDetailView.as_view(),
            name="idea_statistics_detail",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_idea_stats_menu_item() -> MenuItem:
    return MenuItem(
        _("Idea Collection"),
        reverse("idea_statistics"),
        icon_name="clipboard-list",
        order=203,
    )


@hooks.register("register_admin_urls")
def register_close_poll_url() -> list[URLPattern]:
    return [
        path("projects/<int:project_id>/close-poll/", ClosePollView.as_view(), name="close_poll"),
    ]


@hooks.register("register_page_header_buttons")
def close_poll_header_button(page, user, view_name, next_url=None):  # type: ignore[no-untyped-def]
    from publications.models import ProjectPage

    specific = page.specific
    if (
        isinstance(specific, ProjectPage)
        and specific.live
        and specific.is_voting_open
        and page.permissions_for_user(user).can_publish()
    ):
        yield Button(
            _("Close the poll and send the results"),
            reverse("close_poll", args=[page.pk]),
            icon_name="lock",
            priority=40,
        )
