"""Everything the platform stores about a user, for GDPR access and portability (art. 15 and 20).

When a new model stores personal data linked to users, add it here; the test
in core/tests/test_data_export.py fails when a relation to User is missing.
"""

from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.utils import timezone

from core.models import User

# Relations to User that are deliberately left out of the export, with why.
EXCLUDED_RELATIONS = {
    "wagtailusers.UserProfile": "admin interface preferences (language, theme)",
    "wagtailadmin.EditingSession": "transient editor presence, purged automatically",
    "wagtailadmin.FormState": "unsaved editor form state for previews, purged automatically",
    "wagtailcore.Revision": "page history, covered by owned pages",
    "wagtailcore.UploadedFile": "temporary uploads",
    "wagtailcore.WorkflowState": "moderation workflow internals",
    "wagtailcore.TaskState": "moderation workflow internals",
    "wagtailcore.Page": "covered by owned pages",
    "wagtailcore.CommentReply": "covered by admin comments",
    "wagtailcore.PageSubscription": "admin notification settings",
    "wagtaildocs.Document": "uploaded as part of editorial work",
    "wagtailimages.Image": "uploaded as part of editorial work",
    "admin.LogEntry": "Django admin audit log",
    "publications.PollClosure": "editorial action, not personal data",
}


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def _url(page: Any) -> str | None:
    return f"{settings.WAGTAILADMIN_BASE_URL.rstrip('/')}{page.url}" if page and page.url else None


def account(user: User) -> dict[str, Any]:
    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "postal_code": user.postal_code,
        "address": user.address,
        "location": user.location,
        "neighborhood_association": user.association.name if user.association else None,
        "responsible_for_associations": [
            a.name for a in user.responsible_for_associations.order_by("name")
        ],
        "phone_number": user.phone_number,
        "neighborhood": str(user.neighborhood) if user.neighborhood else None,
        "role": user.get_role_display(),
        "subscription": {
            "subscribed": user.is_subscriber,
            "since": _iso(user.subscribed_at),
        },
        "email_verified": user.is_verified,
        "date_joined": _iso(user.created_at),
        "last_updated": _iso(user.updated_at),
        "last_login": _iso(user.last_login),
        "newsletter": {
            "subscribed": user.newsletter_subscription,
            "consent_given_at": _iso(user.newsletter_consent_at),
        },
        "email_notifications": {
            "poll_results": user.notify_poll_results,
            "project_updates": user.notify_project_updates,
            "event_reminders": user.notify_event_reminders,
        },
    }


def participation(user: User) -> dict[str, Any]:
    from publications.models import EventInterest, FormResponse, IdeaResponse

    votes = FormResponse.objects.filter(user=user).select_related("project").order_by("created_at")
    ideas = IdeaResponse.objects.filter(user=user).select_related("project").order_by("created_at")
    interests = (
        EventInterest.objects.filter(user=user).select_related("event").order_by("created_at")
    )
    return {
        "votes": [
            {
                "project": vote.project.title,
                "project_url": _url(vote.project),
                "choice": vote.get_choice_display(),
                "comment": vote.comment,
                "anonymous": vote.anonymize,
                "created_at": _iso(vote.created_at),
                "updated_at": _iso(vote.updated_at),
            }
            for vote in votes
        ],
        "ideas": [
            {
                "project": idea.project.title,
                "project_url": _url(idea.project),
                "idea": idea.description,
                "anonymous": idea.anonymize,
                "created_at": _iso(idea.created_at),
                "updated_at": _iso(idea.updated_at),
            }
            for idea in ideas
        ],
        "events_of_interest": [
            {
                "event": interest.event.title,
                "event_url": _url(interest.event),
                "event_date": _iso(interest.event.event_date),
                "flagged_at": _iso(interest.created_at),
            }
            for interest in interests
        ],
    }


def consents(user: User) -> list[dict[str, Any]]:
    from legal.models import CodeOfConductConsent

    rows = CodeOfConductConsent.objects.filter(user=user).select_related("policy_revision")
    return [
        {
            "document": "Code of conduct",
            "version_of": _iso(row.policy_revision.created_at),
            "accepted_at": _iso(row.consented_at),
            "ip_address": row.consent_ip,
        }
        for row in rows.order_by("consented_at")
    ]


def emails(user: User) -> list[dict[str, Any]]:
    return [
        {
            "type": event.get_event_type_display(),
            "status": event.get_status_display(),
            "sent_at": _iso(event.sent_at),
            # Cleared after EMAIL_EVENT_ANONYMIZE_DAYS.
            "recipient": event.recipient_email or None,
        }
        for event in user.email_events.order_by("created_at")
    ]


def editorial(user: User) -> dict[str, Any]:
    from wagtail.models import Comment, Page

    pages = Page.objects.filter(owner=user).order_by("title")
    comments = Comment.objects.filter(user=user).select_related("page").order_by("created_at")
    return {
        "pages_owned": [{"title": page.title, "url": _url(page)} for page in pages],
        "admin_comments": [
            {
                "page": comment.page.title,
                "text": comment.text,
                "created_at": _iso(comment.created_at),
            }
            for comment in comments
        ],
    }


def api_tokens(user: User) -> list[dict[str, Any]]:
    """Wagtail API tokens: metadata only, never the key or its hash."""
    return [
        {
            "name": token.name,
            "prefix": token.prefix,
            "created_at": _iso(token.created),
            "last_used_at": _iso(token.last_used_at),
            "revoked_at": _iso(token.revoked_at),
        }
        for token in user.api_tokens.order_by("created")  # type: ignore[attr-defined]
    ]


def export_user_data(user: User) -> dict[str, Any]:
    data: dict[str, Any] = {
        "generated_at": _iso(timezone.now()),
        "site": settings.WEBSITE_NAME,
        "account": account(user),
        "participation": participation(user),
        "code_of_conduct_consents": consents(user),
        "emails_sent": emails(user),
        "api_tokens": api_tokens(user),
    }
    if user.can_access_admin():
        data["editorial_activity"] = editorial(user)
    return data
