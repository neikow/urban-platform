import logging

from django.http import Http404, HttpRequest, HttpResponse
from django.urls import URLPattern, path
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.menu import MenuItem
from wagtail.admin.widgets import Button
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail import hooks
from wagtail.models import Page

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
def build_main_menu(request: HttpRequest, menu_items: list[MenuItem]) -> None:
    from core.admin_menu import build_main_menu as build

    build(request, menu_items)


@hooks.register("construct_homepage_panels")
def add_dashboard_panels(request: HttpRequest, panels: list) -> None:
    from core.admin_dashboard import dashboard_panels

    panels.extend(dashboard_panels())


@hooks.register("insert_global_admin_css")
def admin_css() -> str:
    return format_html('<link rel="stylesheet" href="{}">', static("core/css/admin.css"))


# --- Page templates (core/page_templates.py) ---------------------------------------


@hooks.register("register_admin_urls")
def register_page_templates_url() -> list[URLPattern]:
    from core.views.page_templates import PageTemplatesView

    return [
        path("page-templates/<int:page_id>/", PageTemplatesView.as_view(), name="page_templates"),
    ]


@hooks.register("register_page_header_buttons")
def page_templates_header_button(page, user, view_name, next_url=None):  # type: ignore[no-untyped-def]
    from core.page_templates import templates_for

    if templates_for(type(page.specific)) and page.permissions_for_user(user).can_edit():
        yield Button(
            _("Start from a template"),
            reverse("page_templates", args=[page.pk]),
            icon_name="doc-full",
            priority=30,
        )


@hooks.register("before_create_page")
def choose_page_template(
    request: HttpRequest, parent_page: Page, page_class: type[Page]
) -> HttpResponse | None:
    """Before the editor of a new page, offer its templates (GET only: saving posts)."""
    from core.page_templates import get_template, pending_template, templates_for
    from core.views.page_templates import creation_chooser

    if request.method != "GET" or not templates_for(page_class) or "blank" in request.GET:
        return None
    if "template" not in request.GET:
        return creation_chooser(request, parent_page, page_class)
    template = get_template(page_class, request.GET["template"])
    if template is None:
        raise Http404
    pending_template.set((page_class, template))
    return None
