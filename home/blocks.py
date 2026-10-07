"""Home page building blocks.

Two families, grouped in the editor's block picker:

- **Sections** frame editorial content: a label, a title, an introduction and a
  background tone, around text, steps, key figures, quotes or questions.
- **Live content** is filled from the database (open consultations, upcoming
  events, the projects map, key figures), so the home page stays current
  without anyone editing it.

Every block has a description and a preview value for the block picker, and
``home/page_templates.py`` assembles them into ready-made home pages.
"""

from datetime import timedelta
from typing import Any

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from core.blocks import (
    BLOCK_TYPE_CALL_TO_ACTION_BUTTON,
    BLOCK_TYPE_CARDS,
    BLOCK_TYPE_FAQ,
    BLOCK_TYPE_HERO,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_RECENT_PUBLICATIONS,
    BLOCK_TYPE_RICH_TEXT,
    BLOCK_TYPE_TESTIMONIAL_LIST,
    BLOCK_TYPE_TWO_COLUMN,
    BLOCK_TYPE_VERTICAL_SPACER,
    BLOCK_TYPES_AVAILABLE_IN_TWO_COLUMNS,
    AugmentedRichTextBlock,
    BlockTypeList,
    CardListBlock,
    CTAButtonBlock,
    CustomImageBlock,
    FAQBlock,
    HeroBlock,
    RecentPublicationsBlock,
    TestimonialListBlock,
    VerticalSpacerBlock,
    get_two_column_block,
)

GROUP_SECTIONS = _("Sections")
GROUP_LIVE = _("Live content")
GROUP_OTHER = _("Other blocks")

RICH_TEXT_FEATURES = ["h3", "bold", "italic", "link", "ol", "ul"]


class SectionTone(models.TextChoices):
    PLAIN = "plain", _("Plain")
    SAND = "sand", _("Sand")
    NAVY = "navy", _("Navy")


class SectionLayout(models.TextChoices):
    STACKED = "stacked", _("Title above the content")
    SPLIT = "split", _("Title on the left, content on the right")


def format_number(value: int) -> str:
    """12345 -> "12 345", with the narrow no-break space French uses."""
    return f"{value:,}".replace(",", " ")


# --- Section content -----------------------------------------------------------


class SectionTextBlock(blocks.RichTextBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(features=RICH_TEXT_FEATURES, **kwargs)

    class Meta:
        label = _("Text")
        icon = "pilcrow"
        template = "home/blocks/section_text.html"


class StepBlock(blocks.StructBlock):
    title = blocks.CharBlock(label=_("Title"), max_length=80)
    text = blocks.TextBlock(label=_("Text"), required=False)


class StepsBlock(blocks.ListBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(StepBlock(), min_num=2, max_num=6, **kwargs)

    class Meta:
        label = _("Steps")
        icon = "list-ol"
        template = "home/blocks/steps.html"
        description = _("Numbered steps, e.g. how to take part.")


class FigureMetric(models.TextChoices):
    OPEN_CONSULTATIONS = "open_consultations", _("Open consultations")
    PROJECTS = "projects", _("Published projects")
    VOTES = "votes", _("Votes cast")
    IDEAS = "ideas", _("Ideas submitted")
    PARTICIPANTS = "participants", _("People who took part")
    MEMBERS = "members", _("Registered members")
    EVENTS = "events", _("Events")
    CUSTOM = "custom", _("Number typed below")


def compute_metric(metric: str) -> int | None:
    from core.models import User
    from publications.models import EventPage, FormResponse, IdeaResponse, ProjectPage

    if metric == FigureMetric.OPEN_CONSULTATIONS:
        return len(open_projects())
    if metric == FigureMetric.PROJECTS:
        return ProjectPage.objects.live().public().count()
    if metric == FigureMetric.VOTES:
        return FormResponse.objects.count()
    if metric == FigureMetric.IDEAS:
        return IdeaResponse.objects.count()
    if metric == FigureMetric.PARTICIPANTS:
        voters = FormResponse.objects.values_list("user_id", flat=True)
        contributors = IdeaResponse.objects.values_list("user_id", flat=True)
        return len(set(voters) | set(contributors))
    if metric == FigureMetric.MEMBERS:
        return User.objects.filter(is_active=True).count()
    if metric == FigureMetric.EVENTS:
        return EventPage.objects.live().public().count()
    return None


class FigureBlock(blocks.StructBlock):
    metric = blocks.ChoiceBlock(
        label=_("Figure"),
        choices=FigureMetric.choices,
        default=FigureMetric.PROJECTS,
        help_text=_("Counted from the website, so it is always up to date."),
    )
    value = blocks.CharBlock(
        label=_("Number"),
        required=False,
        max_length=12,
        help_text=_("Only for “Number typed below”, e.g. 7 or 1 200."),
    )
    label = blocks.CharBlock(label=_("Label"), max_length=60)


class KeyFiguresBlock(blocks.ListBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(FigureBlock(), min_num=2, max_num=4, **kwargs)

    def get_context(self, value: Any, parent_context: dict | None = None) -> dict:
        context = super().get_context(value, parent_context=parent_context)
        figures = []
        for figure in value:
            number = compute_metric(figure["metric"])
            shown = format_number(number) if number is not None else figure["value"]
            if shown:
                figures.append({"value": shown, "label": figure["label"]})
        context["figures"] = figures
        return context

    class Meta:
        label = _("Key figures")
        icon = "table"
        template = "home/blocks/key_figures.html"
        description = _("Two to four large numbers, counted live from the website.")


class QuoteBlock(blocks.StructBlock):
    quote = blocks.TextBlock(label=_("Quote"))
    author = blocks.CharBlock(label=_("Author"), max_length=80)
    role = blocks.CharBlock(label=_("Role or neighbourhood"), max_length=80, required=False)


class QuotesBlock(blocks.ListBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(QuoteBlock(), min_num=1, max_num=3, **kwargs)

    class Meta:
        label = _("Quotes")
        icon = "openquote"
        template = "home/blocks/quotes.html"
        description = _("What residents say, up to three quotes.")


class SectionFAQBlock(FAQBlock):
    """The FAQ list without its own title: the section provides it."""

    class Meta:
        label = _("Questions and answers")
        icon = "help"
        template = "home/blocks/faq.html"


class SectionContentBlock(blocks.StreamBlock):
    text = SectionTextBlock()
    steps = StepsBlock()
    key_figures = KeyFiguresBlock()
    quotes = QuotesBlock()
    faq = SectionFAQBlock()
    image = CustomImageBlock()
    button = CTAButtonBlock()


class SectionBlock(blocks.StructBlock):
    label = blocks.CharBlock(
        label=_("Small label"),
        required=False,
        max_length=40,
        help_text=_("Shown above the title, e.g. “Who we are”."),
    )
    title = blocks.CharBlock(label=_("Title"), required=False, max_length=120)
    introduction = blocks.TextBlock(label=_("Introduction"), required=False)
    tone = blocks.ChoiceBlock(
        label=_("Background"), choices=SectionTone.choices, default=SectionTone.PLAIN
    )
    layout = blocks.ChoiceBlock(
        label=_("Layout"), choices=SectionLayout.choices, default=SectionLayout.STACKED
    )
    content = SectionContentBlock(label=_("Content"), required=False)

    class Meta:
        label = _("Section")
        icon = "doc-full"
        template = "home/blocks/section.html"
        group = GROUP_SECTIONS
        description = _(
            "A titled part of the page with a background: text, steps, key figures, quotes or questions."
        )
        preview_value = {
            "label": "Participer",
            "title": "Comment ça marche",
            "introduction": "Quatre étapes pour donner votre avis sur l'avenir du quartier.",
            "tone": SectionTone.SAND,
            "layout": SectionLayout.STACKED,
            "content": [
                (
                    "steps",
                    [
                        {"title": "Créez un compte", "text": "Une adresse email suffit."},
                        {"title": "Suivez les projets", "text": "Chaque projet a sa page."},
                        {"title": "Votez ou proposez", "text": "Pendant la consultation."},
                        {
                            "title": "Recevez les résultats",
                            "text": "Par email, si vous le souhaitez.",
                        },
                    ],
                )
            ],
        }


# --- Live content ----------------------------------------------------------------


def open_projects() -> list[Any]:
    """Published projects currently open for votes or ideas, closing soonest first."""
    from publications.models import ParticipationMode, ProjectPage

    projects = (
        ProjectPage.objects.live()
        .public()
        .filter(participation_mode__in=[ParticipationMode.VOTING, ParticipationMode.IDEAS])
        .select_related("hero_image", "poll_closure")
    )
    still_open = [p for p in projects if p.is_voting_open or p.is_ideas_open]
    far_future = timezone.now() + timedelta(days=36500)
    return sorted(still_open, key=lambda p: p.voting_end_date or far_future)


def publications_url(**query: str) -> str:
    """The publications index, optionally filtered, e.g. type="events"."""
    from urllib.parse import urlencode

    from publications.models import PublicationIndexPage

    index = PublicationIndexPage.objects.live().first()
    if index is None:
        return ""
    return index.url + (f"?{urlencode(query)}" if query else "")


class LiveBlock(blocks.StructBlock):
    """Common header fields of the blocks filled from the database."""

    label = blocks.CharBlock(label=_("Small label"), required=False, max_length=40)
    title = blocks.CharBlock(label=_("Title"), max_length=120)

    def get_preview_context(self, value: Any, parent_context: dict | None = None) -> dict:
        # In the block picker, an empty live block explains itself instead of
        # rendering nothing.
        context = super().get_preview_context(value, parent_context=parent_context)
        context["is_block_preview"] = True
        return context

    class Meta:
        group = GROUP_LIVE


class OpenProjectsBlock(LiveBlock):
    limit = blocks.IntegerBlock(
        label=_("Maximum number of projects"), default=3, min_value=1, max_value=6
    )

    def get_context(self, value: Any, parent_context: dict | None = None) -> dict:
        context = super().get_context(value, parent_context=parent_context)
        projects = open_projects()[: value["limit"]]
        context["projects"] = projects
        # Thumbnails only when at least one project has a photo: a column of
        # empty placeholders adds nothing.
        context["show_images"] = any(project.hero_image for project in projects)
        context["projects_url"] = publications_url(type="projects")
        return context

    class Meta:
        label = _("Open consultations")
        icon = "pick"
        template = "home/blocks/open_projects.html"
        description = _(
            "Projects open for votes or ideas, closing soonest first. Hidden when none is open."
        )
        preview_value = {"label": "Participer", "title": "Consultations en cours", "limit": 3}


class UpcomingEventsBlock(LiveBlock):
    limit = blocks.IntegerBlock(
        label=_("Maximum number of events"), default=3, min_value=1, max_value=6
    )

    def get_context(self, value: Any, parent_context: dict | None = None) -> dict:
        from publications.models import EventPage

        context = super().get_context(value, parent_context=parent_context)
        now = timezone.now()
        context["events"] = list(
            EventPage.objects.live()
            .public()
            .filter(Q(event_date__gte=now) | Q(end_date__gte=now))
            .order_by("event_date")[: value["limit"]]
        )
        context["events_url"] = publications_url(type="events")
        return context

    class Meta:
        label = _("Upcoming events")
        icon = "date"
        template = "home/blocks/upcoming_events.html"
        description = _("The next events, soonest first. Hidden when none is planned.")
        preview_value = {"label": "Agenda", "title": "Prochains rendez-vous", "limit": 3}


class ProjectsMapBlock(LiveBlock):
    introduction = blocks.TextBlock(label=_("Introduction"), required=False)

    def get_context(self, value: Any, parent_context: dict | None = None) -> dict:
        from publications.geo import feature_collection, map_config
        from publications.models import ProjectPage

        context = super().get_context(value, parent_context=parent_context)
        projects = (
            ProjectPage.objects.live()
            .public()
            .filter(location__isnull=False)
            .order_by("-first_published_at")
        )
        context["projects_map"] = feature_collection(projects)
        context["map_config"] = map_config()
        return context

    class Meta:
        label = _("Projects map")
        icon = "site"
        template = "home/blocks/projects_map.html"
        description = _("Every located project on a map of the area.")
        preview_value = {
            "label": "Autour de vous",
            "title": "Les projets du quartier",
            "introduction": "",
        }


class JoinBlock(blocks.StructBlock):
    title = blocks.CharBlock(label=_("Title"), max_length=120)
    text = blocks.TextBlock(label=_("Text"), required=False)
    button = blocks.CharBlock(
        label=_("Button for visitors"),
        max_length=40,
        help_text=_("Leads to the registration form."),
    )
    member_button = blocks.CharBlock(
        label=_("Button for signed-in members"),
        max_length=40,
        help_text=_("Leads to their email notification settings."),
    )

    class Meta:
        label = _("Join the platform")
        icon = "user"
        template = "home/blocks/join.html"
        group = GROUP_SECTIONS
        description = _(
            "An invitation to create an account, or to members, to turn on email updates."
        )
        preview_value = {
            "title": "Votre avis compte",
            "text": "Inscrivez-vous pour voter sur les projets, proposer vos idées et être prévenu des résultats.",
            "button": "Créer mon compte",
            "member_button": "Choisir mes notifications",
        }


# --- The home page stream --------------------------------------------------------

# The first blocks predate the sections; their names stay so existing content
# keeps rendering, they are only regrouped in the block picker.
HOME_BLOCK_TYPES: BlockTypeList = [
    (BLOCK_TYPE_HERO, HeroBlock(group=GROUP_SECTIONS)),
    ("section", SectionBlock()),
    ("join", JoinBlock()),
    ("open_projects", OpenProjectsBlock()),
    ("upcoming_events", UpcomingEventsBlock()),
    ("projects_map", ProjectsMapBlock()),
    (BLOCK_TYPE_RECENT_PUBLICATIONS, RecentPublicationsBlock(group=GROUP_LIVE)),
    (BLOCK_TYPE_RICH_TEXT, AugmentedRichTextBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_IMAGE, CustomImageBlock(group=GROUP_OTHER)),
    (
        BLOCK_TYPE_TWO_COLUMN,
        get_two_column_block(
            BLOCK_TYPES_AVAILABLE_IN_TWO_COLUMNS, BLOCK_TYPES_AVAILABLE_IN_TWO_COLUMNS
        )(group=GROUP_OTHER),
    ),
    (BLOCK_TYPE_CARDS, CardListBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_TESTIMONIAL_LIST, TestimonialListBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_FAQ, FAQBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_VERTICAL_SPACER, VerticalSpacerBlock(group=GROUP_OTHER)),
    (BLOCK_TYPE_CALL_TO_ACTION_BUTTON, CTAButtonBlock(group=GROUP_OTHER)),
]
