from dataclasses import dataclass
from typing import Optional, Sequence, Union

from django.core.paginator import Page as PaginatorPage
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
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

    from publications.models.event import EventPage
    from publications.models.project import ProjectPage

    if publication_type == "projects":
        project_ct = ContentType.objects.get_for_model(ProjectPage)
        return publications.filter(real_type=project_ct).order_by("-first_published_at")

    elif publication_type == "events":
        event_ct = ContentType.objects.get_for_model(EventPage)
        return publications.filter(real_type=event_ct).order_by("-eventpage__event_date")

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
