from django.apps import AppConfig
from wagtail.users.apps import WagtailUsersAppConfig


class CoreConfig(AppConfig):
    # Marked default because this module also declares CustomUsersAppConfig;
    # without it Django cannot tell which config the "core" app should use.
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        from wagtail.signals import page_published, page_unpublished

        from core.cache import clear_content_cache

        # Any publish/unpublish can change what the cached list fragments show,
        # so flush the content cache on either.
        page_published.connect(
            clear_content_cache, dispatch_uid="core.cache.clear_content_cache.published"
        )
        page_unpublished.connect(
            clear_content_cache, dispatch_uid="core.cache.clear_content_cache.unpublished"
        )


class CustomUsersAppConfig(WagtailUsersAppConfig):
    """Replaces ``wagtail.users`` to swap in our role-aware user viewset."""

    user_viewset = "core.wagtail_viewsets.UserViewSet"
