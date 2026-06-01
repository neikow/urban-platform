from django.apps import AppConfig
from wagtail.users.apps import WagtailUsersAppConfig


class CoreConfig(AppConfig):
    # Marked default because this module also declares CustomUsersAppConfig;
    # without it Django cannot tell which config the "core" app should use.
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"


class CustomUsersAppConfig(WagtailUsersAppConfig):
    """Replaces ``wagtail.users`` to swap in our role-aware user viewset."""

    user_viewset = "core.wagtail_viewsets.UserViewSet"
