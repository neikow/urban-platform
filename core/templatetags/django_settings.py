from django import template

register = template.Library()


@register.simple_tag()
def get_setting(name):
    from django.conf import settings

    return getattr(settings, name, "")
