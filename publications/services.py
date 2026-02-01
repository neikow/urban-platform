from dataclasses import dataclass
from typing import Any, Optional, Sequence, Union

from django.db.models import Count, Q, QuerySet
from django.core.paginator import Page as PaginatorPage
from django.core.paginator import Paginator
from django.http import HttpRequest

from publications.models.project import ProjectCategory


@dataclass
class PublicationFilters:
    publication_type: str = "all"
    category: Optional[str] = None
    search_query: str = ""
    page_number: Optional[int] = None

    @classmethod
    def from_request(cls, request: HttpRequest) -> "PublicationFilters":
        page_str = request.GET.get("page")
        page_number = int(page_str) if page_str is not None else None
        return cls(
            publication_type=request.GET.get("type", "all"),
            category=request.GET.get("category"),
            search_query=request.GET.get("search", ""),
            page_number=page_number,
        )


def filter_publications_by_type(publications: QuerySet, publication_type: str) -> QuerySet:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.functions import Coalesce
    from django.utils import timezone

    from publications.models.event import EventPage
    from publications.models.project import ProjectPage

    if publication_type == "projects":
        project_ct = ContentType.objects.get_for_model(ProjectPage)
        return publications.filter(real_type=project_ct).order_by("-first_published_at")

    elif publication_type == "events":
        event_ct = ContentType.objects.get_for_model(EventPage)
        now = timezone.now()
        return (
            publications.filter(real_type=event_ct)
            .annotate(effective_end_date=Coalesce("eventpage__end_date", "eventpage__event_date"))
            .filter(effective_end_date__gte=now)
            .order_by("eventpage__event_date")
        )

    return publications.order_by("-first_published_at")


def filter_publications_by_category(publications: QuerySet, category: Optional[str]) -> QuerySet:
    if category and category in [c.value for c in ProjectCategory]:
        return publications.filter(projectpage__category=category)
    return publications


def search_publications(publications: QuerySet, search_query: str) -> QuerySet:
    if search_query:
        return publications.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
    return publications


def paginate_publications(
    publications: Union[QuerySet, Sequence],
    page_number: Optional[int] = None,
    per_page: int = 12,
) -> PaginatorPage:
    paginator = Paginator(publications, per_page)
    return paginator.get_page(page_number)


def get_filtered_publications(
    base_queryset: QuerySet,
    filters: PublicationFilters,
    per_page: int = 12,
) -> PaginatorPage:
    publications = filter_publications_by_type(base_queryset, filters.publication_type)

    if filters.publication_type == "projects":
        publications = filter_publications_by_category(publications, filters.category)

    publications = search_publications(publications, filters.search_query)

    return paginate_publications(publications, filters.page_number, per_page)


def get_vote_results(project: "ProjectPage") -> dict[str, Any]:
    from publications.models.form import FormResponse, VoteChoice

    responses = FormResponse.objects.filter(project=project)
    total_votes = responses.count()

    if total_votes == 0:
        return {
            "total_votes": 0,
            "choices": {choice[0]: {"count": 0, "percentage": 0} for choice in VoteChoice.choices},
        }

    # Count votes per choice
    vote_counts = responses.values("choice").annotate(count=Count("choice"))
    counts_dict = {item["choice"]: item["count"] for item in vote_counts}

    choices_results = {}
    for choice_value, choice_label in VoteChoice.choices:
        count = counts_dict.get(choice_value, 0)
        percentage = round((count / total_votes) * 100, 1) if total_votes > 0 else 0
        choices_results[choice_value] = {
            "count": count,
            "percentage": percentage,
            "label": str(choice_label),
        }

    return {
        "total_votes": total_votes,
        "choices": choices_results,
    }
