from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel

from publications.models.publication import PublicationPage


class EventPage(PublicationPage):
    parent_page_types: list[str] = ["publications.PublicationIndexPage"]
    child_page_types: list[str] = []

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Event")

    @property
    def is_event(self) -> bool:
        return True

    event_date: models.DateTimeField[Any, Any] = models.DateTimeField(
        verbose_name=_("Event Date"),
        help_text=_("Date et heure de début de l'événement"),
    )

    end_date: models.DateTimeField[Any, Any] = models.DateTimeField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
        help_text=_("Date et heure de fin de l'événement (optionnel)"),
    )

    location: models.CharField[str, str] = models.CharField(
        _("Location"),
        max_length=255,
        blank=True,
        help_text=_("Lieu de l'événement"),
    )

    address: models.TextField[str, str] = models.TextField(
        _("Address"),
        blank=True,
        help_text=_("Adresse complète de l'événement"),
    )

    is_online: models.BooleanField[bool, bool] = models.BooleanField(
        _("Online Event"),
        default=False,
        help_text=_("Cochez si l'événement est en ligne"),
    )

    online_link: models.URLField[str, str] = models.URLField(
        _("Online Link"),
        blank=True,
        help_text=_("Lien vers l'événement en ligne (si applicable)"),
    )

    max_participants: models.PositiveIntegerField[int | None, int | None] = (
        models.PositiveIntegerField(
            _("Maximum Participants"),
            null=True,
            blank=True,
            help_text=_("Nombre maximum de participants (laisser vide si illimité)"),
        )
    )

    content_panels = PublicationPage.content_panels + [
        FieldPanel("event_date"),
        FieldPanel("end_date"),
        FieldPanel("location"),
        FieldPanel("address"),
        FieldPanel("is_online"),
        FieldPanel("online_link"),
        FieldPanel("max_participants"),
    ]

    @property
    def is_past(self) -> bool:
        from django.utils import timezone

        return self.event_date < timezone.now()

    @property
    def is_upcoming(self) -> bool:
        return not self.is_past

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
