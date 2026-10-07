from datetime import datetime, time
from typing import Any

from django.db import models
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from wagtail.admin.panels import FieldPanel

from publications.models.publication import PublicationPage


class EventPage(PublicationPage):
    # Ready-made content offered when creating one (core/page_templates.py).
    page_templates = "publications.page_templates.EVENT_TEMPLATES"
    parent_page_types: list[str] = ["publications.PublicationIndexPage"]
    child_page_types: list[str] = []

    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        return _("Event")

    is_event = True

    event_date: models.DateTimeField[Any, Any] = models.DateTimeField(
        verbose_name=_("Event Date"),
        help_text=_("Start date and time of the event"),
    )

    end_date: models.DateTimeField[Any, Any] = models.DateTimeField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
        help_text=_("End date and time of the event (optional)"),
    )

    location: models.CharField[str, str] = models.CharField(
        _("Location"),
        max_length=255,
        blank=True,
        help_text=_("Venue of the event"),
    )

    address: models.TextField[str, str] = models.TextField(
        _("Address"),
        blank=True,
        help_text=_("Full address of the event"),
    )

    is_online: models.BooleanField[bool, bool] = models.BooleanField(
        _("Online Event"),
        default=False,
        help_text=_("Check if the event takes place online"),
    )

    online_link: models.URLField[str, str] = models.URLField(
        _("Online Link"),
        blank=True,
        help_text=_("Link to the online event (if applicable)"),
    )

    max_participants: models.PositiveIntegerField[int | None, int | None] = (
        models.PositiveIntegerField(
            _("Maximum Participants"),
            null=True,
            blank=True,
            help_text=_("Maximum number of participants (leave empty if unlimited)"),
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

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["interest_count"] = self.interests.count()
        context["user_interested"] = (
            request.user.is_authenticated and self.interests.filter(user=request.user).exists()
        )
        return context

    @property
    def is_past(self) -> bool:
        """
        Détermine si un événement est passé.
        - Si end_date existe: l'événement est passé si end_date < maintenant
        - Sinon: l'événement est passé si event_date à 23:59:59 < maintenant
        Cela évite qu'un événement en cours soit marqué comme passé.
        """

        now = timezone.now()

        if self.end_date:
            return self.end_date < now

        # Utilise 23:59:59 du jour de l'événement
        event_day_end = datetime.combine(self.event_date.date(), time(23, 59, 59))
        if timezone.is_aware(self.event_date):
            event_day_end = timezone.make_aware(event_day_end, timezone.get_current_timezone())

        return event_day_end < now

    @property
    def is_ongoing(self) -> bool:
        """Détermine si un événement est en cours (a commencé mais pas encore terminé)."""

        now = timezone.now()
        return self.event_date <= now and not self.is_past

    @property
    def is_upcoming(self) -> bool:
        """Détermine si un événement n'a pas encore commencé."""

        return self.event_date > timezone.now()

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
