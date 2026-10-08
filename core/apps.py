from django.apps import AppConfig
from wagtail.users.apps import WagtailUsersAppConfig


class CoreConfig(AppConfig):
    # Marked default because this module also declares CustomUsersAppConfig;
    # without it Django cannot tell which config the "core" app should use.
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        from wagtail.signals import init_new_page, page_published, page_unpublished

        from core.cache import clear_content_cache
        from core.page_templates import fill_new_page

        # Any publish/unpublish can change what the cached list fragments show,
        # so flush the content cache on either.
        page_published.connect(
            clear_content_cache, dispatch_uid="core.cache.clear_content_cache.published"
        )
        page_unpublished.connect(
            clear_content_cache, dispatch_uid="core.cache.clear_content_cache.unpublished"
        )

        # A page created from a template starts with its content.
        init_new_page.connect(fill_new_page, dispatch_uid="core.page_templates.fill_new_page")

        # Residents follow the association areas: redraw one, and they move with it.
        from django.db.models.signals import post_delete, post_save

        from core.associations import reassign_residents_on_change

        for signal in (post_save, post_delete):
            signal.connect(
                reassign_residents_on_change,
                sender="core.NeighborhoodAssociation",
                dispatch_uid=f"core.associations.reassign_residents.{signal is post_save}",
            )


class CustomUsersAppConfig(WagtailUsersAppConfig):
    """Replaces ``wagtail.users`` to swap in our role-aware user viewset."""

    user_viewset = "core.wagtail_viewsets.UserViewSet"
