from django import template

from core.views.login import LoginForm

register = template.Library()


@register.simple_tag()
def login_form() -> LoginForm:
    return LoginForm()
