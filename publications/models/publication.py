from typing import Any, Self, override

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from core.blocks import BlockTypes


class PublicationPage(Page):
    class Meta:
        verbose_name = _("Publication")
        verbose_name_plural = _("Publications")

    real_type = models.ForeignKey(  # type: ignore[var-annotated]
        ContentType,
        on_delete=models.SET_NULL,
        editable=False,
        null=True,
        related_name="+",
    )

    @override
    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.real_type_id:
            self.real_type = ContentType.objects.get_for_model(type(self))
        super().save(*args, **kwargs)

    def get_real_instance(self) -> Self:
        if self.real_type:
            model_name = self.real_type.model
            if hasattr(self, model_name):
                return getattr(self, model_name)
        return self

    @property
    def is_event(self) -> bool:
        if self._meta.model.__name__ == "EventPage":
            return True
        real_instance = self.get_real_instance()
        if real_instance is not self:
            return real_instance._meta.model.__name__ == "EventPage"
        return False

    @property
    def is_project(self) -> bool:
        if self._meta.model.__name__ == "ProjectPage":
            return True
        real_instance = self.get_real_instance()
        if real_instance is not self:
            return real_instance._meta.model.__name__ == "ProjectPage"
        return False

    @property
    def category(self) -> str | None:
        if self._meta.model.__name__ == "ProjectPage":
            return self.__dict__.get("category")
        real_instance = self.get_real_instance()
        if real_instance is not self:
            return real_instance.__dict__.get("category")
        return None

    def get_category_display(self) -> str:
        if self._meta.model.__name__ == "ProjectPage":
            from publications.models.project import ProjectCategory

            category_value = self.__dict__.get("category")
            if category_value:
                for choice_value, choice_label in ProjectCategory.choices:
                    if choice_value == category_value:
                        return str(choice_label)
            return ""
        real_instance = self.get_real_instance()
        if real_instance is not self and hasattr(real_instance, "get_category_display"):
            return real_instance.get_category_display()
        return ""

    @property
    def event_date(self) -> "models.DateTimeField | None":
        if self._meta.model.__name__ == "EventPage":
            return self.__dict__.get("event_date")
        real_instance = self.get_real_instance()
        if real_instance is not self:
            return real_instance.__dict__.get("event_date")
        return None

    @property
    def is_upcoming(self) -> bool:
        if self._meta.model.__name__ == "EventPage":
            from django.utils import timezone

            event_date = self.__dict__.get("event_date")
            return event_date is not None and event_date >= timezone.now()
        real_instance = self.get_real_instance()
        if real_instance is not self and hasattr(real_instance, "is_upcoming"):
            from django.utils import timezone

            event_date = real_instance.__dict__.get("event_date")
            return event_date is not None and event_date >= timezone.now()
        return False

    description: models.TextField[str, str] = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("A brief description shown in lists."),
    )

    hero_image: models.ForeignKey[Any, Any] = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Hero Image"),
        help_text=_("Main image for this publication"),
    )

    content = StreamField(
        BlockTypes,
        blank=True,
        verbose_name=_("Content"),
        help_text=_("The main content of the page."),
    )

    search_fields = Page.search_fields + [
        index.SearchField("description"),
        index.SearchField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        FieldPanel("hero_image"),
        FieldPanel("content"),
    ]
