from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    CITIZEN = "CITIZEN", _("Citizen")
    ASSOCIATION_MEMBER = "ASSOCIATION_MEMBER", _("Association Member")
    ADMIN = "ADMIN", _("Admin")


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
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
    email = models.EmailField(_("email address"), unique=True)

    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)

    neighborhood = models.ForeignKey(
        "CityNeighborhood",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("neighborhood"),
    )
    postal_code = models.CharField(_("postal code"), max_length=10, blank=True)

    is_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Is the user's email address verified?"),
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=UserRole.choices,  # type: ignore[arg-type] # choices expects str, not TextChoices
        default=UserRole.CITIZEN,
    )

    phone_number = models.CharField(_("phone number"), max_length=20, blank=True)
    newsletter_subscription = models.BooleanField(
        _("newsletter subscription"),
        default=False,
        help_text=_("Does the user want to receive the newsletter?"),
    )

    created_at = models.DateTimeField(_("date joined"), auto_now_add=True)
    updated_at = models.DateTimeField(_("last updated"), auto_now=True)

    # Django permissions
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the admin site."),
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]

