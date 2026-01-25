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

    real_type = models.ForeignKey(
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
        return False

    @property
    def is_project(self) -> bool:
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
