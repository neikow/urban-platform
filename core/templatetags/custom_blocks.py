from django import template

from core.blocks import TextJustification, ImageSize

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


@register.simple_tag
def get_image_config(size_key: ImageSize) -> dict:
    configs = {
        "small": {
            "class": "max-w-sm",
        },
        "medium": {
            "class": "max-w-2xl",
        },
        "large": {
            "class": "max-w-4xl",
        },
        "full": {
            "class": "max-w-full",
        },
    }

    return configs.get(size_key, configs["full"])
