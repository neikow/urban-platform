from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView


class MeView(LoginRequiredMixin, TemplateView):
    template_name = "core/profile.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        context["interesting_events"] = self.get_interesting_events()
        return context

    def get_interesting_events(self) -> list[Any]:
        """Upcoming events the user flagged as interesting, soonest first."""
        from publications.models import EventPage

        now = timezone.now()
        return list(
            EventPage.objects.live()
            .filter(interests__user=self.request.user)
            .filter(Q(end_date__gte=now) | Q(end_date__isnull=True, event_date__gte=now))
            .order_by("event_date")
        )
