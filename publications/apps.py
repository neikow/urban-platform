from django.apps import AppConfig


class PublicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "publications"

    def ready(self) -> None:
        from publications import signals  # noqa: F401  (connects signal handlers)
