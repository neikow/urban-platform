from django.conf import settings
from django.urls import reverse
from wagtail.admin.menu import MenuItem, Menu, SubmenuMenuItem
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail import hooks

from home.models import HomePage
from legal.models import CodeOfConductPage, CookiesPolicyPage, PrivacyPolicyPage, TermsOfServicePage
from pedagogy.models import PedagogyIndexPage
from publications.models import PublicationIndexPage
from .models import NeighborhoodAssociation
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


@hooks.register("register_icons")
def register_icons(icons):
    return icons + ["core/icons/graduation-cap.svg", "core/icons/gavel.svg"]


@hooks.register("construct_main_menu")
def hide_images_menu_item(request, menu_items):
    hidden_names = ["explorer", "reports", "help"]

    admin_settings = [item for item in menu_items if item.name == "settings"][0]

    settings_hidden_names = [
        "sites",
        "redirects",
        "collections",
    ]

    admin_settings.menu.registered_menu_items[:] = [
        item
        for item in admin_settings.menu.registered_menu_items
        if item.name not in settings_hidden_names
    ]

    menu_items[:] = [item for item in menu_items if item.name not in hidden_names]


@hooks.register("register_admin_menu_item")
def register_home_page_edition_menu():
    home_page = HomePage.objects.first()

    return MenuItem(
        _("Page d'accueil"),
        reverse("wagtailadmin_pages:edit", args=[home_page.id]),
        icon_name="home",
        order=0,
    )


@hooks.register("register_admin_menu_item")
def register_publications_menu():
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
def register_pedagogic_entries_menu():
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
def register_legal_menu():
    code_of_conduct = CodeOfConductPage.objects.first()
    cookies_policy = CookiesPolicyPage.objects.first()
    privacy_policy = PrivacyPolicyPage.objects.first()
    terms_of_service = TermsOfServicePage.objects.first()

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
