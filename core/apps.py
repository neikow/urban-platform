from typing import Any

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

        # Page and media rights follow the staff role (core.roles).
        from django.db.models.signals import post_save as user_saved

        from core.roles import sync_role_groups

        def sync_groups(
            sender: type, instance: Any, raw: bool = False, update_fields: Any = None, **kwargs: Any
        ) -> None:
            # Skip fixtures, and partial saves that leave the role alone (e.g. last_login).
            if raw or (update_fields and not {"role", "is_active"} & set(update_fields)):
                return
            sync_role_groups(instance)

        user_saved.connect(
            sync_groups, sender="core.User", dispatch_uid="core.roles.sync_groups", weak=False
        )

        # Audit trail of what Wagtail does not log itself (core.audit).
        from django.contrib.auth.signals import user_logged_in, user_login_failed

        from core.audit import on_logged_in, on_login_failed, on_user_saved

        user_saved.connect(on_user_saved, sender="core.User", dispatch_uid="core.audit.user_saved")
        user_logged_in.connect(on_logged_in, dispatch_uid="core.audit.logged_in")
        user_login_failed.connect(on_login_failed, dispatch_uid="core.audit.login_failed")

        # Every Celery task run is recorded for the admin tasks page.
        from core.task_monitor import connect_signals

        connect_signals()

        # Residents follow the association areas: redraw one, and they move with it.
        from django.db.models.signals import post_delete, post_save

        from core.associations import on_association_deleted, on_association_saved

        post_save.connect(
            on_association_saved,
            sender="core.NeighborhoodAssociation",
            dispatch_uid="core.associations.on_association_saved",
        )
        post_delete.connect(
            on_association_deleted,
            sender="core.NeighborhoodAssociation",
            dispatch_uid="core.associations.on_association_deleted",
        )


class CustomUsersAppConfig(WagtailUsersAppConfig):
    """Replaces ``wagtail.users`` to swap in our role-aware user viewset."""

    user_viewset = "core.wagtail_viewsets.UserViewSet"
