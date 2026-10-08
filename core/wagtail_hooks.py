import logging
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.urls import URLPattern, path
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.menu import MenuItem
from wagtail.admin.widgets import Button
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList
from wagtail import hooks
from wagtail.models import Page

from publications.widgets import GeoJSONMapWidget

from .models import NeighborhoodAssociation, EmailEvent
from .widgets import AddressInput
from django.utils.translation import gettext_lazy as _


class NeighborhoodAssociationForm(WagtailAdminModelForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Draw the other associations' areas underneath, to draw next to them.
        self.fields["area"].widget.reference = lambda: other_association_areas(self.instance.pk)


def other_association_areas(exclude_pk: int | None) -> dict[str, Any]:
    associations = NeighborhoodAssociation.objects.filter(area__isnull=False)
    if exclude_pk is not None:
        associations = associations.exclude(pk=exclude_pk)
    return {"type": "FeatureCollection", "features": [a.area_feature() for a in associations]}


class NeighborhoodAssociationViewSet(ModelViewSet):
    model = NeighborhoodAssociation
    menu_icon = "group"
    add_to_settings_menu = True
    exclude_from_explorer = False
    list_display = ["name", "responsible", "contact_email", "contact_phone", "website"]
    search_fields = ["name", "address", "contact_email", "website"]
    edit_handler = ObjectList(
        [
            FieldPanel("name"),
            FieldPanel("responsible"),
            FieldPanel("address", widget=AddressInput),
            FieldPanel(
                "area",
                widget=GeoJSONMapWidget(
                    markers=False,
                    help_text=_(
                        "Draw the area the association covers: residents living in it are "
                        "attached to the association. The other associations' areas are "
                        "shown in grey, and new points snap to their edges."
                    ),
                ),
            ),
            MultiFieldPanel(
                [FieldPanel("contact_email"), FieldPanel("contact_phone"), FieldPanel("website")],
                heading=_("Contact"),
            ),
        ],
        base_form_class=NeighborhoodAssociationForm,
    )


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


# --- Background tasks page (core/task_monitor.py) ---------------------------------


@hooks.register("register_admin_urls")
def register_tasks_urls() -> list[URLPattern]:
    from core.views.tasks import TasksView, run_task, tasks_status

    return [
        path("tasks/", TasksView.as_view(), name="admin_tasks"),
        path("tasks/status/", tasks_status, name="admin_tasks_status"),
        path("tasks/<slug:key>/run/", run_task, name="admin_tasks_run"),
    ]


@hooks.register("register_settings_menu_item")
def register_tasks_menu_item() -> MenuItem:
    from core.admin_menu import CheckedMenuItem
    from core.views.tasks import can_manage_tasks

    return CheckedMenuItem(
        _("Tasks"),
        reverse("admin_tasks"),
        check=can_manage_tasks,
        name="tasks",
        icon_name="cogs",
        order=900,
    )


# --- Roles (core/roles.py) ------------------------------------------------------


@hooks.register("before_delete_user")
def keep_one_administrator(request: HttpRequest, user: Any) -> HttpResponse | None:
    from django.contrib import messages
    from django.shortcuts import redirect

    from core.roles import is_last_administrator

    if is_last_administrator(user):
        messages.error(request, _("This is the last administrator: name another one first."))
        return redirect("wagtailusers_users:edit", user.pk)
    return None


# --- Audit trail (core/audit.py) ------------------------------------------------


@hooks.register("register_log_actions")
def register_audit_actions(actions: Any) -> None:
    from core.audit import register_actions

    register_actions(actions)


@hooks.register("before_edit_setting")
def remember_setting(request: HttpRequest, instance: Any) -> None:
    import copy

    request.setting_before_edit = copy.copy(instance)  # type: ignore[attr-defined]


@hooks.register("after_edit_setting")
def log_setting_changes(request: HttpRequest, instance: Any) -> None:
    """Wagtail logs that a setting was saved; this adds what changed."""
    from core.audit import audit, settings_changes

    before = getattr(request, "setting_before_edit", None)
    if before is None:
        return
    fields = [f.name for f in instance._meta.concrete_fields if f.editable and not f.is_relation]
    fields = [name for name in fields if name not in ("id",)]
    changes = settings_changes(before, instance, fields)
    if changes:
        audit(instance, "core.settings.change", changes=changes)


@hooks.register("register_admin_urls")
def register_audit_urls() -> list[URLPattern]:
    from core.views.audit import AuditLogResultsView, AuditLogView

    return [
        path("activity-log/", AuditLogView.as_view(), name="audit_log"),
        path("activity-log/results/", AuditLogResultsView.as_view(), name="audit_log_results"),
    ]


@hooks.register("register_settings_menu_item")
def register_audit_menu_item() -> MenuItem:
    from core.admin_menu import CheckedMenuItem

    return CheckedMenuItem(
        _("Activity log"),
        reverse("audit_log"),
        check=lambda request: request.user.has_perm("core.view_audit_log"),
        name="activity-log",
        icon_name="history",
        order=950,
    )
