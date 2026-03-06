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
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_verified", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
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
    is_staff = models.BooleanField(
        _("Staff Status"),
        default=False,
        help_text=_("Designates whether the user can log into the admin site."),
    )

    objects = UserManager()

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
        self.newsletter_subscription = False
        self.is_verified = False

        self.save()
