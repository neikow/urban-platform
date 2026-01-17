from django import template
from django.template.context import BaseContext
from wagtail.models import Site, Page

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

    from legal.models import LegalIndexPage

    legal_index = LegalIndexPage.objects.live().descendant_of(root).first()
    if legal_index:
        return legal_index.get_children().live().in_menu()
    return []
