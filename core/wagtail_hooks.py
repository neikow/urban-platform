from django.http import HttpRequest
from django.urls import reverse
from wagtail.admin.menu import MenuItem, Menu, SubmenuMenuItem
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail import hooks

from home.models import HomePage
from legal.models import CodeOfConductPage, CookiesPolicyPage, PrivacyPolicyPage, TermsOfServicePage
from pedagogy.models import PedagogyIndexPage
from publications.models import PublicationIndexPage
from .models import NeighborhoodAssociation, EmailEvent
from django.utils.translation import gettext_lazy as _


class NeighborhoodAssociationViewSet(ModelViewSet):
    model = NeighborhoodAssociation
    menu_icon = "group"
    add_to_settings_menu = True
    exclude_from_explorer = False
    list_display = ["neighborhood", "contact_email", "contact_phone", "website"]
    search_fields = ["neighborhood__name", "contact_email", "website"]
    form_fields = ["neighborhood", "contact_email", "contact_phone", "website"]


@hooks.register("register_admin_viewset")
def register_neighborhood_association_viewset() -> NeighborhoodAssociationViewSet:
    return NeighborhoodAssociationViewSet("neighborhood_association")


class EmailEventViewSet(ModelViewSet):
    model = EmailEvent
    menu_icon = "mail"
    add_to_settings_menu = True
    exclude_from_explorer = False
    list_display = ["user", "event_type", "status", "recipient_email", "sent_at"]
    search_fields = ["user__email", "recipient_email", "event_type", "status"]
    form_fields = ["user", "event_type", "status", "recipient_email", "sent_at"]


@hooks.register("register_admin_viewset")
def register_email_event_viewset() -> EmailEventViewSet:
    return EmailEventViewSet("register_email_event_viewset")


@hooks.register("register_icons")
def register_icons(icons: list[str]) -> list[str]:
    return icons + ["core/icons/graduation-cap.svg", "core/icons/gavel.svg"]


@hooks.register("construct_main_menu")
def hide_menu_items(request: HttpRequest, menu_items: list[MenuItem | SubmenuMenuItem]) -> None:
    hidden_names = ["explorer", "reports", "help"]

    admin_settings = [item for item in menu_items if item.name == "settings"]

    if admin_settings:
        admin_setting = admin_settings[0]

        settings_hidden_names = [
            "sites",
            "redirects",
            "collections",
        ]

        admin_setting.menu.registered_menu_items[:] = [
            item
            for item in admin_setting.menu.registered_menu_items
            if item.name not in settings_hidden_names
        ]

    menu_items[:] = [item for item in menu_items if item.name not in hidden_names]


@hooks.register("register_admin_menu_item")
def register_home_page_edition_menu() -> MenuItem:
    home_page = HomePage.objects.first()

    return MenuItem(
        _("Page d'accueil"),
        reverse("wagtailadmin_pages:edit", args=[home_page.id]),
        icon_name="home",
        order=0,
    )


@hooks.register("register_admin_menu_item")
def register_publications_menu() -> MenuItem:
    index_page = PublicationIndexPage.objects.first()

    submenu = Menu(
        items=[
            MenuItem(
                _("Page d'accueil"),
                reverse("wagtailadmin_pages:edit", args=[index_page.id]),
                icon_name="home",
                order=100,
            ),
            MenuItem(
                _("Liste"),
                reverse("wagtailadmin_explore", args=[index_page.id]),
                icon_name="folder-open-inverse",
                order=200,
            ),
            MenuItem(
                _("Ajouter"),
                reverse("wagtailadmin_pages:add_subpage", args=[index_page.id]),
                icon_name="plus",
                order=300,
            ),
        ]
    )
    return SubmenuMenuItem(_("Publications"), submenu, icon_name="doc-full-inverse", order=100)


@hooks.register("register_admin_menu_item")
def register_pedagogic_entries_menu() -> MenuItem:
    index_page = PedagogyIndexPage.objects.first()

    submenu = Menu(
        items=[
            MenuItem(
                _("Page d'accueil"),
                reverse("wagtailadmin_pages:edit", args=[index_page.id]),
                icon_name="home",
                order=100,
            ),
            MenuItem(
                _("Liste"),
                reverse("wagtailadmin_explore", args=[index_page.id]),
                icon_name="folder-open-inverse",
                order=200,
            ),
            MenuItem(
                _("Ajouter"),
                reverse("wagtailadmin_pages:add_subpage", args=[index_page.id]),
                icon_name="plus",
                order=300,
            ),
        ]
    )
    return SubmenuMenuItem(_("Fiches Pédagogiques"), submenu, icon_name="graduation-cap", order=200)


@hooks.register("register_admin_menu_item")
def register_legal_menu() -> MenuItem:
    code_of_conduct = CodeOfConductPage.objects.live().first()
    cookies_policy = CookiesPolicyPage.objects.live().first()
    privacy_policy = PrivacyPolicyPage.objects.live().first()
    terms_of_service = TermsOfServicePage.objects.live().first()

    submenu = Menu(
        items=[
            MenuItem(
                _("Charte de conduite"),
                reverse("wagtailadmin_pages:edit", args=[code_of_conduct.id]),
                icon_name="doc-full-inverse",
                order=100,
            ),
            MenuItem(
                _("Conditions d'utilisation"),
                reverse("wagtailadmin_pages:edit", args=[terms_of_service.id]),
                icon_name="doc-full-inverse",
                order=200,
            ),
            MenuItem(
                _("Politique de cookies"),
                reverse("wagtailadmin_pages:edit", args=[cookies_policy.id]),
                icon_name="doc-full-inverse",
                order=300,
            ),
            MenuItem(
                _("Politique de confidentialité"),
                reverse("wagtailadmin_pages:edit", args=[privacy_policy.id]),
                icon_name="doc-full-inverse",
                order=400,
            ),
        ]
    )
    return SubmenuMenuItem(_("Légal"), submenu, icon_name="gavel", order=300)
