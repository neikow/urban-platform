"""Audit trail: who did what, and when.

Built on Wagtail's audit log, which already records page and model actions
(created, edited, submitted for moderation, approved, rejected, published,
moved, deleted…) and shows them in the activity log (core.views.audit).
This module adds the actions Wagtail does not see:

- account changes: role, superuser status, activation (memberships are
  logged by Wagtail, like any model edited in the admin);
- security events: staff logins and failed logins, password and email
  changes, personal data exports, account deletions;
- background tasks started by hand;
- emails sent to users: poll results, project news (publications);
- map updates (publications).

Inside the admin, Wagtail fills in the acting user. Elsewhere it is passed
explicitly, or left empty for actions of the system (scheduled tasks).
Logging never makes the logged action fail.
"""

import logging
from datetime import timedelta
from typing import Any

from django.db import DatabaseError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.log_actions import LogFormatter, log

logger = logging.getLogger(__name__)

# Security events hold personal data (who logged in, from where): kept one year.
# The other entries are the history of the content and of the accounts.
SECURITY_RETENTION_DAYS = 365
SECURITY_ACTIONS_PREFIX = "core.auth."

# Account fields whose changes are logged, with their labels.
TRACKED_USER_FIELDS = ("role", "is_superuser", "is_active")


def audit(instance: Any, action: str, user: Any = None, **data: Any) -> None:
    """Log ``action`` on ``instance``; ``user`` defaults to the admin request's user."""
    try:
        kwargs: dict[str, Any] = {"data": data} if data else {}
        if user is not None and getattr(user, "is_authenticated", False):
            kwargs["user"] = user
        log(instance, action, **kwargs)
    except DatabaseError:
        logger.exception("Could not log %s on %r", action, instance)


def client_ip(request: Any) -> str | None:
    from core.utils import get_client_ip

    return get_client_ip(request) if request is not None else None


# --- action labels and messages (register_log_actions hook) ---------------------


def _role_label(value: str | None) -> str:
    from core.models import UserRole

    if value is None:
        return "—"
    try:
        return str(UserRole(value).label)
    except ValueError:
        return value


class RoleChangeFormatter(LogFormatter):
    label = _("Change role")

    def format_message(self, log_entry: Any) -> str:
        try:
            return _("Role changed from %(old)s to %(new)s") % {
                "old": _role_label(log_entry.data["old"]),
                "new": _role_label(log_entry.data["new"]),
            }
        except KeyError:
            return str(_("Role changed"))


class SubscriptionChangeFormatter(LogFormatter):
    """Entries from before memberships had their own records (core.models.Membership)."""

    label = _("Change subscription")

    def format_message(self, log_entry: Any) -> str:
        if log_entry.data.get("new"):
            return str(_("Marked as subscriber"))
        return str(_("No longer a subscriber"))


class SuperuserChangeFormatter(LogFormatter):
    label = _("Change superuser status")

    def format_message(self, log_entry: Any) -> str:
        if log_entry.data.get("new"):
            return str(_("Made superuser"))
        return str(_("No longer superuser"))


class ActivationFormatter(LogFormatter):
    label = _("Activate or deactivate")

    def format_message(self, log_entry: Any) -> str:
        if log_entry.data.get("new"):
            return str(_("Account activated"))
        return str(_("Account deactivated"))


class LoginFormatter(LogFormatter):
    label = _("Log in")

    def format_message(self, log_entry: Any) -> str:
        ip = log_entry.data.get("ip")
        return _("Logged in from %(ip)s") % {"ip": ip} if ip else str(_("Logged in"))


class LoginFailedFormatter(LogFormatter):
    label = _("Failed login")

    def format_message(self, log_entry: Any) -> str:
        ip = log_entry.data.get("ip")
        return _("Wrong password, from %(ip)s") % {"ip": ip} if ip else str(_("Wrong password"))


class EmailChangeFormatter(LogFormatter):
    label = _("Change email")

    def format_message(self, log_entry: Any) -> str:
        try:
            return _("Email changed from %(old)s to %(new)s") % log_entry.data
        except KeyError:
            return str(_("Email changed"))


class TaskLaunchFormatter(LogFormatter):
    label = _("Start a task")

    def format_message(self, log_entry: Any) -> str:
        return _("Started “%(task)s”") % {"task": log_entry.data.get("label", "")}


class SettingsChangeFormatter(LogFormatter):
    label = _("Change settings")

    def format_message(self, log_entry: Any) -> str:
        changes = log_entry.data.get("changes", {})
        if not changes:
            return str(_("Settings saved"))
        return ", ".join(f"{field}: {old} → {new}" for field, (old, new) in changes.items())


def register_actions(actions: Any) -> None:
    actions.register_action("core.user.role_change")(RoleChangeFormatter)
    actions.register_action("core.user.subscription_change")(SubscriptionChangeFormatter)
    actions.register_action("core.user.superuser_change")(SuperuserChangeFormatter)
    actions.register_action("core.user.activation_change")(ActivationFormatter)
    actions.register_action("core.auth.login")(LoginFormatter)
    actions.register_action("core.auth.login_failed")(LoginFailedFormatter)
    actions.register_action(
        "core.auth.password_change", _("Change password"), _("Password changed")
    )
    actions.register_action("core.auth.password_reset", _("Reset password"), _("Password reset"))
    actions.register_action("core.auth.email_change")(EmailChangeFormatter)
    actions.register_action(
        "core.auth.data_export", _("Export personal data"), _("Downloaded their personal data")
    )
    actions.register_action(
        "core.auth.account_delete", _("Delete own account"), _("Deleted their account")
    )
    actions.register_action("core.task.launch")(TaskLaunchFormatter)
    actions.register_action("core.settings.change")(SettingsChangeFormatter)


# --- account changes (User post_save) -------------------------------------------


def snapshot(user: Any) -> dict[str, Any]:
    """The tracked fields that are loaded (deferred ones would query the database)."""
    return {name: user.__dict__[name] for name in TRACKED_USER_FIELDS if name in user.__dict__}


USER_FIELD_ACTIONS = {
    "role": "core.user.role_change",
    "is_superuser": "core.user.superuser_change",
    "is_active": "core.user.activation_change",
}


def on_user_saved(
    sender: Any, instance: Any, created: bool, raw: bool = False, **kwargs: Any
) -> None:
    from core.models import UserRole

    if raw:
        return
    before = getattr(instance, "audit_snapshot", None) or {}
    after = snapshot(instance)
    if created:
        # A new account: only a staff role or superuser status is worth noting.
        if instance.role != UserRole.CITIZEN:
            audit(instance, "core.user.role_change", old=None, new=instance.role)
        if instance.is_superuser:
            audit(instance, "core.user.superuser_change", old=False, new=True)
    elif instance.deleted_at is None:  # soft deletion is logged as such
        for name, action in USER_FIELD_ACTIONS.items():
            if name in before and name in after and before[name] != after[name]:
                audit(instance, action, old=before[name], new=after[name])
    instance.audit_snapshot = after


# --- security events -------------------------------------------------------------


def on_logged_in(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Staff logins only: residents' logins are not worth keeping."""
    from core.models import UserRole

    if user.has_role(UserRole.EDITOR):
        audit(user, "core.auth.login", user=user, ip=client_ip(request))


def on_login_failed(
    sender: Any, credentials: dict[str, Any], request: Any = None, **kwargs: Any
) -> None:
    """Failed logins on staff accounts: a sign someone is guessing a password."""
    from core.models import User, UserRole

    email = credentials.get("email") or credentials.get("username")
    if not email:
        return
    target = User.objects.filter(email__iexact=email).first()
    if target is not None and target.has_role(UserRole.EDITOR):
        audit(target, "core.auth.login_failed", ip=client_ip(request))


def _shown(value: Any) -> Any:
    if isinstance(value, bool | int | float) or value is None:
        return value
    text = str(value)
    return text if len(text) <= 120 else text[:119] + "…"


def settings_changes(before: Any, after: Any, fields: list[str]) -> dict[str, list[Any]]:
    """The fields that changed between two settings instances, for core.settings.change."""
    return {
        str(after._meta.get_field(name).verbose_name): [
            _shown(getattr(before, name)),
            _shown(getattr(after, name)),
        ]
        for name in fields
        if getattr(before, name) != getattr(after, name)
    }


def forget_user(user: Any) -> None:
    """After an account deletion: drop the email from the entries about that account.

    The entries stay (the history of the site), under the anonymized label; the
    security events lose their details, which may hold the former email.
    """
    from django.contrib.contenttypes.models import ContentType
    from wagtail.models import ModelLogEntry

    entries = ModelLogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(user), object_id=str(user.pk)
    )
    entries.update(label=str(user))
    entries.filter(action__startswith=SECURITY_ACTIONS_PREFIX).update(data={})


def prune_security_events() -> int:
    """Delete security events older than SECURITY_RETENTION_DAYS. Returns how many."""
    from wagtail.models import ModelLogEntry

    cutoff = timezone.now() - timedelta(days=SECURITY_RETENTION_DAYS)
    deleted, _counts = ModelLogEntry.objects.filter(
        action__startswith=SECURITY_ACTIONS_PREFIX, timestamp__lt=cutoff
    ).delete()
    return deleted
