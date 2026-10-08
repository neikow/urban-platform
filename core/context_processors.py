from typing import TypedDict
from django.conf import settings

from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject


class ProjectSettings(TypedDict):
    website_name: str
    territory: SimpleLazyObject


def project_settings(request: HttpRequest) -> ProjectSettings:
    from core.models import Territory

    return {
        "website_name": settings.WEBSITE_NAME,
        # Loaded only by the templates that name the area.
        "territory": SimpleLazyObject(lambda: Territory.current(request)),
    }
