from datetime import datetime
from typing import Generic, TypeVar, Iterable

from django.contrib.sitemaps import Sitemap
from wagtail.models import Page
from home.models import HomePage
from publications.models import PublicationIndexPage, ProjectPage, EventPage
from pedagogy.models import PedagogyIndexPage, PedagogyCardPage

from legal.models import (
    LegalIndexPage,
    TermsOfServicePage,
    PrivacyPolicyPage,
    CookiesPolicyPage,
    CodeOfConductPage,
)

PageType = TypeVar("PageType", bound=Page)


class WagtailPageSitemap(Sitemap, Generic[PageType]):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.5

    model: type[PageType] | None = None

    def items(self) -> Iterable[PageType]:  # type: ignore[override]
        if self.model is None:
            return Page.objects.none()
        return self.model.objects.live().public().order_by("-last_published_at")

    def location(self, item: Page) -> str:  # type: ignore[override]
        return item.url or "/"

    def lastmod(self, item: Page) -> datetime:  # type: ignore[override]
        return item.last_published_at


class HomePageSitemap(WagtailPageSitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self) -> Iterable[HomePage]:  # type: ignore[override]
        return HomePage.objects.live().public()


class LegalPagesSitemap(WagtailPageSitemap):
    priority = 0.3
    changefreq = "monthly"

    def items(self) -> Iterable[Page]:  # type: ignore[override]
        page_types: list[type[Page]] = [
            LegalIndexPage,
            TermsOfServicePage,
            PrivacyPolicyPage,
            CookiesPolicyPage,
            CodeOfConductPage,
        ]
        pks: list[int] = []
        for model in page_types:
            pks.extend(model.objects.live().public().values_list("pk", flat=True))
        return Page.objects.filter(pk__in=pks).specific().order_by("path")


class PedagogyIndexSitemap(WagtailPageSitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self) -> Iterable[PedagogyIndexPage]:  # type: ignore[override]
        return PedagogyIndexPage.objects.live().public()


class PedagogyCardSitemap(WagtailPageSitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self) -> Iterable[PedagogyCardPage]:  # type: ignore[override]
        return PedagogyCardPage.objects.live().public().order_by("-last_published_at")


class PublicationIndexSitemap(WagtailPageSitemap):
    priority = 0.7
    changefreq = "daily"

    def items(self) -> Iterable[PublicationIndexPage]:  # type: ignore[override]
        return PublicationIndexPage.objects.live().public()


class ProjectPageSitemap(WagtailPageSitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self) -> Iterable[ProjectPage]:  # type: ignore[override]
        return ProjectPage.objects.live().public().order_by("-last_published_at")


class EventPageSitemap(WagtailPageSitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self) -> Iterable[EventPage]:  # type: ignore[override]
        return EventPage.objects.live().public().order_by("-last_published_at")


SITEMAPS = {
    "home": HomePageSitemap,
    "legal": LegalPagesSitemap,
    "pedagogy-index": PedagogyIndexSitemap,
    "pedagogy-cards": PedagogyCardSitemap,
    "publications-index": PublicationIndexSitemap,
    "projects": ProjectPageSitemap,
    "events": EventPageSitemap,
}
