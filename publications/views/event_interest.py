from typing import cast

from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views import View

from core.models import User
from publications.models import EventInterest, EventPage
from publications.views.mixins import ParticipationMixin, json_error


class EventInterestView(ParticipationMixin, View):
    """Flag or unflag an event as interesting. GET is public and returns the counter."""

    requires_authentication = False
    # Flagging interest is not a contribution: no code of conduct needed, but a
    # verified email is, since reminders are sent to it.
    requires_code_of_conduct = False
    # Nor a membership: it only asks for a reminder.
    requires_membership = False

    def get_event(self, event_id: int) -> EventPage | None:
        return EventPage.objects.live().filter(pk=event_id).first()

    def state(self, request: HttpRequest, event: EventPage) -> JsonResponse:
        interested = (
            request.user.is_authenticated
            and EventInterest.objects.filter(user=cast(User, request.user), event=event).exists()
        )
        return JsonResponse(
            {
                "success": True,
                "interested": interested,
                "count": EventInterest.objects.filter(event=event).count(),
            }
        )

    def get(self, request: HttpRequest, event_id: int) -> JsonResponse:
        event = self.get_event(event_id)
        if event is None:
            return json_error(_("Event not found"), status=404)
        return self.state(request, event)

    def post(self, request: HttpRequest, event_id: int) -> JsonResponse:
        event = self.get_event(event_id)
        if event is None:
            return json_error(_("Event not found"), status=404)
        if event.is_past:
            return json_error(_("This event is over."), status=400)
        EventInterest.objects.get_or_create(user=cast(User, request.user), event=event)
        return self.state(request, event)

    def delete(self, request: HttpRequest, event_id: int) -> JsonResponse:
        event = self.get_event(event_id)
        if event is None:
            return json_error(_("Event not found"), status=404)
        EventInterest.objects.filter(user=cast(User, request.user), event=event).delete()
        return self.state(request, event)
