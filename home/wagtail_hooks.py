from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.widgets import Button

from home.views import HomePageTemplatesView


@hooks.register("register_admin_urls")
def register_home_page_templates_url() -> list[URLPattern]:
    return [
        path(
            "home-page/<int:page_id>/templates/",
            HomePageTemplatesView.as_view(),
            name="home_page_templates",
        ),
    ]


@hooks.register("register_page_header_buttons")
def home_page_templates_header_button(page, user, view_name, next_url=None):  # type: ignore[no-untyped-def]
    from home.models import HomePage

    if isinstance(page.specific, HomePage) and page.permissions_for_user(user).can_edit():
        yield Button(
            _("Start from a template"),
            reverse("home_page_templates", args=[page.pk]),
            icon_name="doc-full",
            priority=30,
        )
