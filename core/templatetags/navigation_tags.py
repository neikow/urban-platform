from dataclasses import dataclass
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise

from django import template
from django.template.context import BaseContext
from wagtail.models import Site, Page
from wagtail.templatetags.wagtailcore_tags import pageurl

from legal.models import LegalIndexPage

register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context: BaseContext) -> Site | None:
    request = context.get("request")

    if request is not None:
        site = Site.find_for_request(request)
        if site is not None:
            return site.root_page

    default_site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if default_site is not None:
        return default_site.root_page

    return None


@register.simple_tag(takes_context=True)
def get_legal_pages(context: BaseContext) -> list[Page]:
    root = get_site_root(context)
    if not root:
        return []

    legal_index = LegalIndexPage.objects.live().descendant_of(root).first()
    if legal_index:
        return legal_index.get_children().live().in_menu()
    return []


@dataclass
class MenuItem:
    title: StrOrPromise
    url: str
    is_active: bool


@register.simple_tag(takes_context=True)
def get_navigation_menu_items(
    context: BaseContext,
) -> list[MenuItem]:
    root = get_site_root(context)
    request = context["request"]
    if not request:
        return []

    home_url = pageurl(context, root) or "/"

    menu_items = [
        MenuItem(
            title=_("Home"),
            url=home_url,
            is_active=request.path == home_url,
        )
    ]
    for page in root.get_children().live().in_menu():
        page_url = pageurl(context, page)
        menu_items.append(
            MenuItem(
                title=page.title,
                url=page_url or "#",
                is_active=request.path == page_url,
            )
        )

    return menu_items
