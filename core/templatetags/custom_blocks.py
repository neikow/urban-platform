from django import template

from core.blocks import TextJustification

register = template.Library()


@register.simple_tag()
def text_justification_class(justification: str) -> str:
    if justification == TextJustification.CENTER:
        return "text-center"
    elif justification == TextJustification.RIGHT:
        return "text-right"
    elif justification == TextJustification.LEFT:
        return "text-left"
    elif justification == TextJustification.JUSTIFY:
        return "text-justify"
    else:
        return ""
