from typing import Any

from wagtail.signals import page_published

from publications.models import ProjectPage


def on_project_published(sender: type, instance: ProjectPage, **kwargs: Any) -> None:
    from publications.project_updates import queue_new_updates

    queue_new_updates(instance)


page_published.connect(on_project_published, sender=ProjectPage)
