from django import template
from wagtail.models import Site

register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context):
    request = context.get("request")

    if request is not None:
        site = Site.find_for_request(request)
        if site is not None:
            return site.root_page

    default_site = (
        Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    )
    if default_site is not None:
        return default_site.root_page

    return None
