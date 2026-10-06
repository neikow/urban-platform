from datetime import timedelta

import pytest
from django.utils import timezone

from core.models import User
from home.models import HomePage
from publications.models import (
    FormResponse,
    ParticipationMode,
    ProjectPage,
    PublicationIndexPage,
    VoteChoice,
)
from publications.services import get_final_vote_results


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
    return index


def make_project(index, *, closed: bool) -> ProjectPage:
    end = timezone.now() + timedelta(days=-1 if closed else 1)
    project = ProjectPage(
        title="Closed" if closed else "Open",
        slug="closed" if closed else "open",
        participation_mode=ParticipationMode.VOTING,
        voting_end_date=end,
    )
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


def vote(project: ProjectPage, *choices: str) -> None:
    for i, choice in enumerate(choices):
        user = User.objects.create_user(
            email=f"v{i}@example.com", password="x", first_name="V", last_name=str(i)
        )
        FormResponse.objects.create(user=user, project=project, choice=choice)


@pytest.mark.django_db
class TestFinalResults:
    def test_closed_poll_shows_results_to_anonymous_visitors(self, client, index):
        project = make_project(index, closed=True)
        vote(project, VoteChoice.FAVORABLE, VoteChoice.FAVORABLE, VoteChoice.UNFAVORABLE)

        content = client.get(project.url).content.decode()

        assert 'id="vote-final-results"' in content
        assert "66,7" in content  # French formatting in the text
        assert 'value="66.7"' in content  # but a valid number for <progress>
        assert 'id="vote-login-prompt"' not in content
        assert 'data-can-participate="false"' in content

    def test_closed_poll_without_votes(self, client, index):
        project = make_project(index, closed=True)

        response = client.get(project.url)

        assert 'id="vote-final-results"' in response.content.decode()
        assert response.context["final_vote_results"]["total_votes"] == 0

    def test_open_poll_hides_results(self, client, index):
        project = make_project(index, closed=False)
        vote(project, VoteChoice.FAVORABLE)

        response = client.get(project.url)

        assert 'id="vote-final-results"' not in response.content.decode()
        assert "final_vote_results" not in response.context

    def test_ordered_results_cover_every_choice(self, index):
        project = make_project(index, closed=True)
        vote(project, VoteChoice.RATHER_FAVORABLE)

        results = get_final_vote_results(project)

        assert [row["value"] for row in results["ordered"]] == [
            "FAVORABLE",
            "RATHER_FAVORABLE",
            "RATHER_UNFAVORABLE",
            "UNFAVORABLE",
        ]
        assert results["ordered"][1]["percentage"] == 100.0
