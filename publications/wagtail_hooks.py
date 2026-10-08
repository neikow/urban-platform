from typing import Any

from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
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


@hooks.register("register_admin_urls")
def register_map_tiles_refresh_url() -> list[URLPattern]:
    from publications.views.map_tiles import refresh_map_tiles

    return [path("map-tiles/refresh/", refresh_map_tiles, name="map_tiles_refresh")]


@hooks.register("register_log_actions")
def register_publication_log_actions(actions: Any) -> None:
    from wagtail.log_actions import LogFormatter

    class PollCloseFormatter(LogFormatter):
        label = _("Close a poll")

        def format_message(self, log_entry: Any) -> str:
            if log_entry.data.get("reason") == "MANUAL":
                return str(_("Poll closed by hand"))
            return str(_("Poll closed at its end date"))

    class PollResultsFormatter(LogFormatter):
        label = _("Send poll results")

        def format_message(self, log_entry: Any) -> str:
            return _("Results emailed to %(count)s voters") % {
                "count": log_entry.data.get("recipients", 0)
            }

    class ProjectNewsFormatter(LogFormatter):
        label = _("Send project news")

        def format_message(self, log_entry: Any) -> str:
            return _("“%(title)s” emailed to %(count)s followers") % {
                "title": log_entry.data.get("title", ""),
                "count": log_entry.data.get("recipients", 0),
            }

    class MapUpdateFormatter(LogFormatter):
        label = _("Update the map")

        def format_message(self, log_entry: Any) -> str:
            return _("Map data updated to %(build)s") % {"build": log_entry.data.get("build", "")}

    actions.register_action("publications.poll.close")(PollCloseFormatter)
    actions.register_action("publications.poll.results_sent")(PollResultsFormatter)
    actions.register_action("publications.project_update.sent")(ProjectNewsFormatter)
    actions.register_action("publications.map_tiles.update")(MapUpdateFormatter)
