from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template import engines
from django.test import RequestFactory
from django.utils import timezone

from core.models import User
from home.blocks import HOME_BLOCK_TYPES, FigureMetric, JoinBlock, format_number, open_projects
from home.models import HomePage
from publications.models import (
    EventPage,
    FormResponse,
    ParticipationMode,
    PollClosure,
    PollClosureReason,
    ProjectPage,
    PublicationIndexPage,
    VoteChoice,
)

BLOCKS = dict(HOME_BLOCK_TYPES)


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


def make_project(index, title, mode=ParticipationMode.VOTING, ends_in_days=None, **kwargs):
    project = ProjectPage(
        title=title,
        slug=title.lower().replace(" ", "-"),
        participation_mode=mode,
        voting_end_date=timezone.now() + timedelta(days=ends_in_days) if ends_in_days else None,
        **kwargs,
    )
    index.add_child(instance=project)
    project.save_revision().publish()
    return project


def make_event(index, title, in_days):
    start = timezone.now() + timedelta(days=in_days)
    event = EventPage(
        title=title, slug=title.lower().replace(" ", "-"), event_date=start, end_date=start
    )
    index.add_child(instance=event)
    event.save_revision().publish()
    return event


def render(block_type, value, user=None):
    request = RequestFactory().get("/")
    request.user = user or AnonymousUser()
    block = BLOCKS[block_type]
    return block.render(block.to_python(value), context={"request": request})


@pytest.mark.django_db
class TestPreviews:
    """Every block offered with a preview renders it, so the block picker never breaks."""

    @pytest.mark.parametrize(
        "block_type",
        [name for name, block in HOME_BLOCK_TYPES if getattr(block.meta, "preview_value", None)],
    )
    def test_preview_value_is_valid_and_renders(self, rf, block_type):
        block = BLOCKS[block_type]
        value = block.normalize(block.meta.preview_value)
        block.clean(value)

        request = rf.get("/")
        request.user = AnonymousUser()
        context = block.get_preview_context(value, parent_context={"request": request})
        html = engines["django"].from_string("{% load wagtailcore_tags %}{% include_block value %}")
        assert html.render({**context, "value": block.bind(value)}, request).strip()


@pytest.mark.django_db
class TestOpenProjects:
    def test_lists_open_projects_closing_soonest_first(self, index):
        later = make_project(index, "Plus tard", ends_in_days=20)
        sooner = make_project(index, "Bientot", ends_in_days=2)
        ideas = make_project(index, "Idees", mode=ParticipationMode.IDEAS)

        assert open_projects() == [sooner, later, ideas]

    def test_leaves_out_closed_and_non_participative_projects(self, index):
        make_project(index, "Termine", ends_in_days=-1)
        make_project(index, "Sans vote", mode=ParticipationMode.NONE)
        closed = make_project(index, "Clos", ends_in_days=5)
        PollClosure.objects.create(project=closed, reason=PollClosureReason.MANUAL)

        assert open_projects() == []

    def test_block_lists_them_with_their_deadline(self, index):
        make_project(index, "Jardin partage", ends_in_days=3, description="Un jardin.")

        html = render("open_projects", {"label": "", "title": "Consultations", "limit": 3})

        assert "Jardin partage" in html
        assert "?type=projects" in html

    def test_block_renders_nothing_when_none_is_open(self, index):
        assert (
            render("open_projects", {"label": "", "title": "Consultations", "limit": 3}).strip()
            == ""
        )


@pytest.mark.django_db
class TestUpcomingEvents:
    def test_lists_future_events_soonest_first(self, index):
        make_event(index, "Plus tard", in_days=10)
        make_event(index, "Bientot", in_days=1)
        make_event(index, "Passe", in_days=-5)

        html = render("upcoming_events", {"label": "", "title": "Agenda", "limit": 3})

        assert html.index("Bientot") < html.index("Plus tard")
        assert "Passe" not in html

    def test_renders_nothing_without_events(self, index):
        assert render("upcoming_events", {"label": "", "title": "Agenda", "limit": 3}).strip() == ""


@pytest.mark.django_db
class TestKeyFigures:
    def figures_html(self, figures):
        section = {
            "label": "",
            "title": "En chiffres",
            "introduction": "",
            "tone": "navy",
            "layout": "stacked",
            "content": [{"type": "key_figures", "value": figures}],
        }
        return render("section", section)

    def test_counts_from_the_website(self, index):
        project = make_project(index, "Jardin", ends_in_days=3)
        voter = User.objects.create_user(email="v@example.com", password="pass12345")
        FormResponse.objects.create(user=voter, project=project, choice=VoteChoice.FAVORABLE)

        html = self.figures_html(
            [
                {"metric": FigureMetric.PROJECTS, "value": "", "label": "Projets"},
                {"metric": FigureMetric.VOTES, "value": "", "label": "Votes"},
            ]
        )

        assert ">1</dd>" in html.replace("\n", "").replace(" ", "")
        assert "Projets" in html and "Votes" in html

    def test_typed_numbers_and_empty_ones(self, db):
        html = self.figures_html(
            [
                {"metric": FigureMetric.CUSTOM, "value": "12", "label": "CIQ"},
                {"metric": FigureMetric.CUSTOM, "value": "", "label": "Oublié"},
            ]
        )

        assert "12" in html
        assert "Oublié" not in html

    def test_format_number(self):
        assert format_number(12345) == "12 345"


@pytest.mark.django_db
class TestJoin:
    VALUE = JoinBlock().meta.preview_value

    def test_visitors_are_sent_to_registration(self):
        assert 'href="/auth/register/"' in render("join", self.VALUE)

    def test_members_are_sent_to_their_notifications(self):
        member = User.objects.create_user(email="m@example.com", password="pass12345")

        html = render("join", self.VALUE, user=member)

        assert 'href="/auth/me/edit/#notifications"' in html
        assert self.VALUE["member_button"] in html
