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


@register.simple_tag
def get_image_config(size_key):
    """
    Maps a block size choice to specific rendition rules and CSS classes.
    """
    configs = {
        "small": {
            "rendition": "width-400",
            "class": "max-w-sm",
        },
        "medium": {
            "rendition": "width-800",
            "class": "max-w-2xl",
        },
        "large": {
            "rendition": "width-1200",
            "class": "max-w-4xl",
        },
        "full": {
            "rendition": "width-1600",
            "class": "max-w-full",
        },
    }
    # Fallback to full width if the key is missing
    return configs.get(size_key, configs["full"])
