"""The admin sidebar, in one place.

Grouped by task rather than by app:

    Page d'accueil
    Actualités            › page, list, new project, new event
    Informations utiles   › page, list, new card
    Pages du site         › À propos and legal pages
    Participation         › votes, ideas
    Médiathèque           › images, documents
    Paramètres            › Wagtail settings: announcement, users…
    Documentation

Every entry is shown only to people who can use it (page permissions,
model permissions), and a submenu disappears when none of its entries is
shown: association members, who have fewer rights than administrators,
see fewer entries. Pages that do not exist yet are skipped.

``build_main_menu`` (``construct_main_menu`` hook) drops the Wagtail
defaults this menu replaces and adds its entries. They are built once and
cached, like Wagtail's own registered entries; ``menu_entries.cache_clear()``
rebuilds them (tests).
"""

from collections.abc import Callable
from functools import cache
from typing import Any

from django.http import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.documents.wagtail_hooks import DocumentsMenuItem
from wagtail.images.wagtail_hooks import ImagesMenuItem
from wagtail.models import Page

# Wagtail entries this menu replaces or that editors do not need.
HIDDEN_TOP_LEVEL = {"explorer", "reports", "help", "images", "documents"}
# Settings managed in code (groups and workflows come from migrations, the
# site has a single locale).
HIDDEN_SETTINGS = {
    "sites",
    "redirects",
    "collections",
    "workflows",
    "workflow-tasks",
    "groups",
    "locales",
}


class CheckedMenuItem(MenuItem):
    """A menu entry shown only when ``check(request)`` is true."""

    def __init__(self, *args: Any, check: Callable[[HttpRequest], bool], **kwargs: Any):
        self.check = check
        super().__init__(*args, **kwargs)

    def is_shown(self, request: HttpRequest) -> bool:
        return self.check(request)


def edit_page(
    label: StrOrPromise,
    page: Page | None,
    order: int,
    icon: str = "doc-full",
    name: str | None = None,
) -> MenuItem | None:
    if page is None:
        return None
    return CheckedMenuItem(
        label,
        reverse("wagtailadmin_pages:edit", args=[page.pk]),
        check=lambda request: page.permissions_for_user(request.user).can_edit(),
        icon_name=icon,
        order=order,
        name=name,
    )


def list_children(label: StrOrPromise, page: Page, order: int) -> MenuItem:
    return CheckedMenuItem(
        label,
        reverse("wagtailadmin_explore", args=[page.pk]),
        check=lambda request: page.permissions_for_user(request.user).can_edit(),
        icon_name="list-ul",
        order=order,
    )


def add_child(label: StrOrPromise, parent: Page, page_class: type[Page], order: int) -> MenuItem:
    return CheckedMenuItem(
        label,
        reverse(
            "wagtailadmin_pages:add",
            args=[page_class._meta.app_label, page_class._meta.model_name, parent.pk],
        ),
        check=lambda request: parent.permissions_for_user(request.user).can_add_subpage(),
        icon_name="plus",
        order=order,
    )


def submenu(
    label: StrOrPromise, items: list[MenuItem | None], icon: str, order: int, name: str
) -> SubmenuMenuItem | None:
    available = [item for item in items if item is not None]
    if not available:
        return None
    return SubmenuMenuItem(label, Menu(items=available), icon_name=icon, order=order, name=name)


def has_admin_access(request: HttpRequest) -> bool:
    return request.user.has_perm("wagtailadmin.access_admin")


def can_see_participation_stats(request: HttpRequest) -> bool:
    return request.user.has_perm("core.view_participation_stats")


@cache
def menu_entries() -> tuple[MenuItem, ...]:
    from about.models import AboutCommissionPage, AboutDevTeamPage, AboutWebsitePage
    from home.models import HomePage
    from legal.models import (
        CodeOfConductPage,
        CookiesPolicyPage,
        PrivacyPolicyPage,
        TermsOfServicePage,
    )
    from pedagogy.models import PedagogyCardPage, PedagogyIndexPage
    from publications.models import EventPage, ProjectPage, PublicationIndexPage

    news = PublicationIndexPage.objects.first()
    useful = PedagogyIndexPage.objects.first()

    entries: list[MenuItem | None] = [
        edit_page(
            _("Home page"), HomePage.objects.first(), order=100, icon="home", name="home-page"
        ),
        news
        and submenu(
            _("News"),
            [
                edit_page(_("“News” page"), news, order=100, icon="home"),
                list_children(_("All publications"), news, order=200),
                add_child(_("New project"), news, ProjectPage, order=300),
                add_child(_("New event"), news, EventPage, order=400),
            ],
            icon="doc-full-inverse",
            order=200,
            name="news",
        ),
        useful
        and submenu(
            _("Useful information"),
            [
                edit_page(_("“Useful information” page"), useful, order=100, icon="home"),
                list_children(_("All cards"), useful, order=200),
                add_child(_("New card"), useful, PedagogyCardPage, order=300),
            ],
            icon="graduation-cap",
            order=300,
            name="useful-information",
        ),
        submenu(
            _("Site pages"),
            [
                edit_page(_("The platform"), AboutWebsitePage.objects.first(), order=100),
                edit_page(
                    _("The urban planning commission"),
                    AboutCommissionPage.objects.first(),
                    order=110,
                ),
                edit_page(_("The development team"), AboutDevTeamPage.objects.first(), order=120),
                edit_page(
                    _("Code of conduct"), CodeOfConductPage.objects.first(), order=200, icon="gavel"
                ),
                edit_page(
                    _("Terms of service"),
                    TermsOfServicePage.objects.first(),
                    order=210,
                    icon="gavel",
                ),
                edit_page(
                    _("Cookies policy"), CookiesPolicyPage.objects.first(), order=220, icon="gavel"
                ),
                edit_page(
                    _("Privacy policy"), PrivacyPolicyPage.objects.first(), order=230, icon="gavel"
                ),
            ],
            icon="doc-full",
            order=400,
            name="site-pages",
        ),
        submenu(
            _("Participation"),
            [
                CheckedMenuItem(
                    _("Votes"),
                    reverse("vote_statistics"),
                    check=can_see_participation_stats,
                    name="votes",
                    icon_name="success",
                    order=100,
                ),
                CheckedMenuItem(
                    _("Ideas"),
                    reverse("idea_statistics"),
                    check=can_see_participation_stats,
                    name="ideas",
                    icon_name="clipboard-list",
                    order=200,
                ),
            ],
            icon="group",
            order=500,
            name="participation",
        ),
        submenu(
            _("Media library"),
            [
                ImagesMenuItem(
                    _("Images"),
                    reverse("wagtailimages:index"),
                    name="images",
                    icon_name="image",
                    order=100,
                ),
                DocumentsMenuItem(
                    _("Documents"),
                    reverse("wagtaildocs:index"),
                    name="documents",
                    icon_name="doc-full-inverse",
                    order=200,
                ),
            ],
            icon="image",
            order=600,
            name="media",
        ),
        CheckedMenuItem(
            _("Documentation"),
            reverse("docs_index"),
            check=has_admin_access,
            name="documentation",
            icon_name="help",
            order=11000,
        ),
    ]
    return tuple(entry for entry in entries if entry)


def build_main_menu(request: HttpRequest, menu_items: list[MenuItem]) -> None:
    for item in menu_items:
        if item.name == "settings" and isinstance(item, SubmenuMenuItem):
            item.menu.registered_menu_items[:] = [
                entry
                for entry in item.menu.registered_menu_items
                if entry.name not in HIDDEN_SETTINGS
            ]
    menu_items[:] = [item for item in menu_items if item.name not in HIDDEN_TOP_LEVEL]
    # construct_main_menu receives the entries already filtered for the
    # request, so ours are filtered here too.
    menu_items.extend(entry for entry in menu_entries() if entry.is_shown(request))
