from datetime import datetime
from functools import cached_property

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.search import index

from core.toc import TableOfContentsItem, generate_header_ids, get_table_of_contents
from publications.models.publication import PublicationPage


DEFAULT_VOTE_QUESTION = _("What is your opinion on this project?")


class ProjectCategory(models.TextChoices):
    URBAN_PLANNING = "URBAN_PLANNING", _("Urban Planning")
    ENVIRONMENT = "ENVIRONMENT", _("Environment")
    MOBILITY = "MOBILITY", _("Mobility")
    HOUSING = "HOUSING", _("Housing")
    CULTURE = "CULTURE", _("Culture")
    SPORT = "SPORT", _("Sport")
    EDUCATION = "EDUCATION", _("Education")
    HEALTH = "HEALTH", _("Health")
    SOCIAL = "SOCIAL", _("Social")
    ECONOMY = "ECONOMY", _("Economy")
    OTHER = "OTHER", _("Other")


class ParticipationMode(models.TextChoices):
    """How residents may participate on a project.

    Voting and idea collection are mutually exclusive: a project still in its
    early stages collects ideas, while a more mature one is put to a vote.
    Switching mode never deletes responses already collected for the other one.
    """

    NONE = "NONE", _("No participation")
    VOTING = "VOTING", _("Voting")
    IDEAS = "IDEAS", _("Idea collection")


class ProjectPage(PublicationPage):
    parent_page_types: list[str] = ["publications.PublicationIndexPage"]
    child_page_types: list[str] = []

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Project")

    @property
    def is_project(self) -> bool:
        return True

    category: models.CharField[str, str] = models.CharField(
        _("Category"),
        max_length=30,
        choices=ProjectCategory.choices,
        default=ProjectCategory.OTHER,
    )

    participation_mode: models.CharField[str, str] = models.CharField(
        _("Participation mode"),
        max_length=20,
        choices=ParticipationMode.choices,
        default=ParticipationMode.VOTING,
        help_text=_(
            "Voting lets residents give an opinion; idea collection lets them "
            "propose ideas on a project still in its early stages. The two are "
            "mutually exclusive — switching keeps responses already collected."
        ),
    )

    voting_end_date: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        _("Voting End Date"),
        null=True,
        blank=True,
        help_text=_("Leave empty for no end date (only applies to voting)"),
    )

    show_toc: models.BooleanField[bool, bool] = models.BooleanField(
        _("Show table of contents"),
        default=True,
        help_text=_("Display the table of contents in the sidebar"),
    )

    search_fields = PublicationPage.search_fields + [
        index.SearchField("category"),
    ]

    content_panels = PublicationPage.content_panels + [
        FieldPanel("category"),
        InlinePanel("external_links", label=_("External Links")),
        FieldPanel("participation_mode"),
        FieldPanel("voting_end_date"),
        FieldPanel("show_toc"),
    ]

    @property
    def enable_voting(self) -> bool:
        """Backward-compatible flag: True when the project is in voting mode."""
        return self.participation_mode == ParticipationMode.VOTING

    @property
    def enable_ideas(self) -> bool:
        """True when the project collects ideas instead of votes."""
        return self.participation_mode == ParticipationMode.IDEAS

    def clean(self) -> None:
        super().clean()

        for block in self.content:
            if block.block_type in ("text", "rich_text"):
                generate_header_ids(block)

    @property
    def vote_question(self) -> str:
        """Return the standard vote question for all projects."""
        return str(DEFAULT_VOTE_QUESTION)

    @property
    def is_voting_open(self) -> bool:
        """Check if voting is still open for this project."""
        if not self.enable_voting:
            return False
        if self.voting_end_date is None:
            return True

        return timezone.now() <= self.voting_end_date

    @property
    def is_ideas_open(self) -> bool:
        """Idea collection has no deadline; it is open whenever the mode is active."""
        return self.enable_ideas

    @cached_property
    def has_external_links(self) -> bool:
        """Check if this project has any external links."""
        return self.external_links.exists()

    @property
    def table_of_contents(self) -> list[TableOfContentsItem]:
        return get_table_of_contents(self.content)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
