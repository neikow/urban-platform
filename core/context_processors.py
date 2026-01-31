from typing import TypedDict
from django.conf import settings

from django.http import HttpRequest


class ProjectSettings(TypedDict):
    website_name: str


def project_settings(request: HttpRequest) -> ProjectSettings:
    return {"website_name": settings.WEBSITE_NAME}
