from typing import Any, TypedDict

from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject, lazy


class ProjectSettings(TypedDict):
    website_name: Any
    branding: SimpleLazyObject
    territory: SimpleLazyObject


def project_settings(request: HttpRequest) -> ProjectSettings:
    from core.branding import current, site_name
    from core.models import Territory

    # Loaded only by the templates that use them.
    return {
        "website_name": lazy(site_name, str)(request),
        "branding": SimpleLazyObject(lambda: current(request)),
        "territory": SimpleLazyObject(lambda: Territory.current(request)),
    }
