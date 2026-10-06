from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from core.models import NotificationDispatch, User
from home.models import HomePage
from publications.models import (
    FormResponse,
    ParticipationMode,
    PollClosure,
    PollClosureReason,
    ProjectPage,
    PublicationIndexPage,
    VoteChoice,
)
from publications.polls import close_expired_polls, close_poll, send_poll_results_now


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
    return index


def make_project(index, slug="vote", end_in_days=None) -> ProjectPage:
    project = ProjectPage(
        title=slug.title(),
        slug=slug,
        participation_mode=ParticipationMode.VOTING,
        voting_end_date=timezone.now() + timedelta(days=end_in_days)
        if end_in_days is not None
        else None,
    )
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


def voter(email, choice, project, **prefs) -> User:
    user = User.objects.create_user(
        email=email, password="x", first_name="V", last_name="W", is_verified=True, **prefs
    )
    FormResponse.objects.create(user=user, project=project, choice=choice)
    return user


@pytest.fixture
def queued():
    """Capture queued emails instead of sending them."""
    with mock.patch("core.notifications.tasks.send_notification_email") as task:
        yield task.delay


@pytest.mark.django_db
class TestClosing:
    def test_manual_close_stops_voting_and_survives_republishing(self, index, queued):
        project = make_project(index)
        old_revision = project.latest_revision

        close_poll(project, PollClosureReason.MANUAL)
        old_revision.publish()  # an editor republishes an older draft

        project = ProjectPage.objects.get(pk=project.pk)
        assert project.is_voting_open is False

    def test_close_is_idempotent(self, index, queued):
        project = make_project(index)

        first = close_poll(project, PollClosureReason.MANUAL)
        second = close_poll(project, PollClosureReason.END_DATE)

        assert first.pk == second.pk
        assert PollClosure.objects.get().reason == PollClosureReason.MANUAL

    def test_expired_polls_are_closed_automatically(self, index, queued):
        expired = make_project(index, "expired", end_in_days=-1)
        make_project(index, "running", end_in_days=3)
        make_project(index, "open-ended")

        assert close_expired_polls() == 1
        assert list(PollClosure.objects.values_list("project_id", flat=True)) == [expired.pk]
        assert close_expired_polls() == 0

    def test_closing_sends_results_to_opted_in_voters_once(
        self, index, queued, django_capture_on_commit_callbacks
    ):
        project = make_project(index)
        wants = voter("wants@example.com", VoteChoice.FAVORABLE, project, notify_poll_results=True)
        voter("silent@example.com", VoteChoice.UNFAVORABLE, project)

        with django_capture_on_commit_callbacks(execute=True):
            close_poll(project, PollClosureReason.MANUAL)
        send_poll_results_now(project)  # a second trigger sends nothing

        assert queued.call_count == 1
        user_id, kind, subject, template, context = queued.call_args.args
        assert user_id == wants.pk
        assert kind == "poll_results"
        assert template == "emails/notifications/poll_results.html"
        assert context["total_votes"] == 2
        assert [row["percentage"] for row in context["rows"]] == [50.0, 0, 0, 50.0]
        assert NotificationDispatch.objects.filter(key=f"project:{project.pk}").count() == 1


@pytest.mark.django_db
class TestAdminAction:
    @pytest.fixture
    def admin(self, db):
        return User.objects.create_superuser(
            email="admin@example.com", password="x", first_name="A", last_name="D"
        )

    def test_edit_page_offers_closing_an_open_poll(self, client, index, admin):
        project = make_project(index)
        client.force_login(admin)

        content = client.get(f"/admin/pages/{project.pk}/edit/").content.decode()

        assert f"/admin/projects/{project.pk}/close-poll/" in content

    def test_confirm_then_close(
        self, client, index, admin, queued, django_capture_on_commit_callbacks
    ):
        project = make_project(index)
        client.force_login(admin)
        url = f"/admin/projects/{project.pk}/close-poll/"

        assert client.get(url).status_code == 200
        assert not PollClosure.objects.exists()

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(url)

        assert response.status_code == 302
        closure = PollClosure.objects.get()
        assert (closure.reason, closure.closed_by) == (PollClosureReason.MANUAL, admin)

    def test_requires_publish_permission(self, client, index):
        project = make_project(index)
        citizen = User.objects.create_user(
            email="c@example.com", password="x", first_name="C", last_name="D"
        )
        client.force_login(citizen)

        response = client.post(f"/admin/projects/{project.pk}/close-poll/")

        assert response.status_code in (302, 403)  # no admin access at all
        assert not PollClosure.objects.exists()


@pytest.mark.django_db
def test_closed_poll_shows_final_results(client, index):
    project = make_project(index)
    PollClosure.objects.create(project=project, reason=PollClosureReason.MANUAL)

    assert 'id="vote-final-results"' in client.get(project.url).content.decode()


def test_results_email_renders():
    from django.template.loader import render_to_string

    html = render_to_string(
        "emails/notifications/poll_results.html",
        {
            "user": User(first_name="Nora"),
            "project_title": "Jardin",
            "project_url": "https://example.com/jardin/",
            "question": "Quel est votre avis ?",
            "total_votes": 3,
            "rows": [{"label": "Favorable", "count": 2, "percentage": 66.7}],
            "unsubscribe_url": "https://example.com/u/",
            "preferences_url": "https://example.com/p/",
        },
    )

    assert "Jardin" in html
    assert "Nora" in html
    assert "https://example.com/u/" in html
