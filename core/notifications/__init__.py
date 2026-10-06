"""Opt-in email notifications: poll results, project updates, event reminders.

Each kind maps to a boolean preference on the user. Emails carry a signed
one-click unsubscribe link for their kind, and batches are recorded in
NotificationDispatch so they are never sent twice.
"""

from enum import StrEnum

from django.utils.translation import gettext_lazy as _

from core.models import EmailEventType


class NotificationKind(StrEnum):
    POLL_RESULTS = "poll_results"
    PROJECT_UPDATE = "project_update"
    EVENT_REMINDER = "event_reminder"

    @property
    def preference_field(self) -> str:
        return {
            NotificationKind.POLL_RESULTS: "notify_poll_results",
            NotificationKind.PROJECT_UPDATE: "notify_project_updates",
            NotificationKind.EVENT_REMINDER: "notify_event_reminders",
        }[self]

    @property
    def email_event_type(self) -> str:
        return {
            NotificationKind.POLL_RESULTS: EmailEventType.POLL_RESULTS,
            NotificationKind.PROJECT_UPDATE: EmailEventType.PROJECT_UPDATE,
            NotificationKind.EVENT_REMINDER: EmailEventType.EVENT_REMINDER,
        }[self]

    @property
    def label(self) -> str:
        return str(
            {
                NotificationKind.POLL_RESULTS: _("poll results"),
                NotificationKind.PROJECT_UPDATE: _("project updates"),
                NotificationKind.EVENT_REMINDER: _("event reminders"),
            }[self]
        )
