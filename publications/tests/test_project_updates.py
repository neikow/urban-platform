from datetime import date
from unittest import mock

import pytest
from django.template.loader import render_to_string

from core.models import User
from home.models import HomePage
from publications.models import (
    FormResponse,
    IdeaResponse,
    ParticipationMode,
    ProjectPage,
    ProjectUpdate,
    PublicationIndexPage,
    VoteChoice,
)


@pytest.fixture
def project(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
    project = ProjectPage(
        title="Jardin", slug="jardin", participation_mode=ParticipationMode.VOTING
    )
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


def user(email, **prefs) -> User:
    return User.objects.create_user(
        email=email, password="x", first_name="P", last_name="Q", is_verified=True, **prefs
    )


@pytest.fixture
def queued():
    with mock.patch("core.notifications.tasks.send_notification_email") as task:
        yield task.delay


def edit_and_publish(project, update=None):
    """Like the page editor: start from the latest revision, change it, publish."""
    page = ProjectPage.objects.get(pk=project.pk).get_latest_revision_as_object()
    if update is not None:
        page.updates.add(update)
    return page.save_revision().publish()


def publish_with_update(project, title, notify=True, when=None):
    return edit_and_publish(
        project,
        ProjectUpdate(
            title=title,
            body="Les travaux commencent.",
            date=when or date.today(),
            notify_participants=notify,
        ),
    )


@pytest.mark.django_db
class TestProjectUpdateEmails:
    def test_new_update_reaches_opted_in_participants(
        self, project, queued, django_capture_on_commit_callbacks
    ):
        voter = user("voter@example.com", notify_project_updates=True)
        contributor = user("idea@example.com", notify_project_updates=True)
        silent = user("silent@example.com")
        FormResponse.objects.create(user=voter, project=project, choice=VoteChoice.FAVORABLE)
        FormResponse.objects.create(user=silent, project=project, choice=VoteChoice.FAVORABLE)
        IdeaResponse.objects.create(user=contributor, project=project, description="Un banc")

        with django_capture_on_commit_callbacks(execute=True):
            publish_with_update(project, "Début des travaux")

        recipients = {call.args[0] for call in queued.call_args_list}
        assert recipients == {voter.pk, contributor.pk}
        _uid, kind, subject, template, context = queued.call_args.args
        assert (kind, template) == ("project_update", "emails/notifications/project_update.html")
        assert subject == "Jardin : Début des travaux" or subject == "Jardin: Début des travaux"
        assert context["project_url"].endswith("/jardin/#suivi")

    def test_republishing_does_not_resend(
        self, project, queued, django_capture_on_commit_callbacks
    ):
        FormResponse.objects.create(
            user=user("v@example.com", notify_project_updates=True),
            project=project,
            choice=VoteChoice.FAVORABLE,
        )
        with django_capture_on_commit_callbacks(execute=True):
            publish_with_update(project, "Début des travaux")
        with django_capture_on_commit_callbacks(execute=True):
            edit_and_publish(project)

        assert queued.call_count == 1

    def test_unticked_update_is_not_sent(self, project, queued, django_capture_on_commit_callbacks):
        FormResponse.objects.create(
            user=user("v@example.com", notify_project_updates=True),
            project=project,
            choice=VoteChoice.FAVORABLE,
        )

        with django_capture_on_commit_callbacks(execute=True):
            publish_with_update(project, "Réunion de 2025", notify=False)

        queued.assert_not_called()


@pytest.mark.django_db
def test_timeline_lists_updates_newest_first(client, project):
    publish_with_update(project, "Concertation", when=date(2026, 3, 1))
    publish_with_update(project, "Début des travaux", when=date(2026, 9, 1))

    content = client.get(project.url).content.decode()

    assert 'id="suivi"' in content
    assert content.index("Début des travaux") < content.index("Concertation")


def test_update_email_renders():
    html = render_to_string(
        "emails/notifications/project_update.html",
        {
            "user": User(first_name="Nora"),
            "project_title": "Jardin",
            "project_url": "https://example.com/jardin/#suivi",
            "update_title": "Début des travaux",
            "update_body": "Ligne 1\nLigne 2",
            "unsubscribe_url": "https://example.com/u/",
        },
    )

    assert "Début des travaux" in html
    assert "Ligne 1<br>Ligne 2" in html
