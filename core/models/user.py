from __future__ import annotations
from typing import Any
import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    CITIZEN = "CITIZEN", _("Citizen")
    ASSOCIATION_MEMBER = "ASSOCIATION_MEMBER", _("Association Member")
    ADMIN = "ADMIN", _("Admin")


class UserManager(BaseUserManager["User"]):
    def get_queryset(self) -> models.QuerySet["User"]:
        """Override to exclude soft-deleted users by default."""
        return super().get_queryset().filter(deleted_at__isnull=True)

    def with_deleted(self) -> models.QuerySet["User"]:
        """Return all users including soft-deleted ones."""
        return super().get_queryset()

    def deleted_only(self) -> models.QuerySet["User"]:
        """Return only soft-deleted users."""
        return super().get_queryset().filter(deleted_at__isnull=False)

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_verified", True)

        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    objects: UserManager = UserManager()  # type: ignore[assignment]

    email = models.EmailField(_("Email Address"), unique=True)
    uuid = models.UUIDField(_("UUID"), unique=True, default=uuid.uuid4, editable=False)

    first_name = models.CharField(_("First Name"), max_length=150)
    last_name = models.CharField(_("Last Name"), max_length=150)

    neighborhood = models.ForeignKey(
        "CityNeighborhood",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("Neighborhood"),
    )
    postal_code = models.CharField(_("Postal Code"), max_length=10, blank=True)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    # Filled from the address (core.geocoding); places the user in an association's area.
    location = models.JSONField(_("Location"), null=True, blank=True, editable=False)
    association = models.ForeignKey(
        "NeighborhoodAssociation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residents",
        verbose_name=_("Neighborhood Association"),
        help_text=_("The association whose area contains the user's address."),
    )

    is_verified = models.BooleanField(
        _("Email Verified"),
        default=False,
        help_text=_("Is the user's email address verified?"),
    )
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=UserRole.choices,  # type: ignore[arg-type] # choices expects str, not TextChoices
        default=UserRole.CITIZEN,
    )

    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)
    newsletter_subscription = models.BooleanField(
        _("Newsletter Subscription"),
        default=False,
        help_text=_("Does the user want to receive the newsletter?"),
    )
    newsletter_consent_at = models.DateTimeField(
        _("Newsletter consent date"),
        null=True,
        blank=True,
        help_text=_(
            "When the user last agreed to receive the newsletter (GDPR proof of consent). "
            "Empty if they are not subscribed, or subscribed before this date was recorded."
        ),
    )

    # Email notifications, all opt-in (see core.notifications).
    notify_poll_results = models.BooleanField(
        _("Poll results"),
        default=False,
        help_text=_("Email the results when a poll I voted in closes."),
    )
    notify_project_updates = models.BooleanField(
        _("Project updates"),
        default=False,
        help_text=_("Email the news of projects I voted on or shared an idea about."),
    )
    notify_event_reminders = models.BooleanField(
        _("Event reminders"),
        default=False,
        help_text=_("Email a reminder the day before events I am interested in."),
    )

    created_at = models.DateTimeField(_("Date Joined"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Last Updated"), auto_now=True)
    deleted_at = models.DateTimeField(
        _("Deleted At"),
        null=True,
        blank=True,
        help_text=_("When the user account was soft-deleted. NULL if not deleted."),
    )

    # Django permissions
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )

    @property
    def is_staff(self) -> bool:
        """Deprecated compatibility shim for ``django.contrib.admin``.

        The stored ``is_staff`` field was removed. The Django admin
        (``/django-admin/``) is reserved for superusers; Wagtail admin access is
        governed by the ``wagtailadmin.access_admin`` permission, derived from
        the user's role by :class:`core.auth_backends.RolePermissionsBackend`.
        """
        return self.is_superuser

    def can_access_admin(self) -> bool:
        """Whether the user may enter the Wagtail admin.

        True for superusers and for any role granted ``wagtailadmin.access_admin``.
        """
        return self.has_perm("wagtailadmin.access_admin")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email.split("@")[0]

    def set_newsletter_subscription(self, subscribed: bool) -> None:
        """Change the subscription and keep the consent date in step (not saved)."""
        from django.utils import timezone

        if subscribed and not self.newsletter_subscription:
            self.newsletter_consent_at = timezone.now()
        elif not subscribed:
            self.newsletter_consent_at = None
        self.newsletter_subscription = subscribed

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.is_active = False
        self.set_unusable_password()

        # Anonymize personal data
        self.first_name = "Utilisateur"
        self.last_name = "Supprimé"
        self.email = f"deleted.{self.uuid}@deleted.local"
        self.phone_number = ""
        self.address = ""
        self.location = None
        self.association = None
        self.newsletter_subscription = False
        self.newsletter_consent_at = None
        self.notify_poll_results = False
        self.notify_project_updates = False
        self.notify_event_reminders = False
        self.is_verified = False

        self.save()
