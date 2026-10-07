import hashlib

from django.db import models
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField


class AnnouncementStyle(models.TextChoices):
    INFO = "info", _("Information")
    WARNING = "warning", _("Warning")
    IMPORTANT = "important", _("Important")


@register_setting(icon="info-circle")
class Announcement(BaseGenericSetting):
    """A message shown in a band at the top of every page of the website.

    Visitors can close it. It stays closed until the message or its style
    changes: the band carries a :attr:`version` and the dismissed one is kept
    in a cookie (see ``core.templatetags.announcement_tags``).
    """

    enabled = models.BooleanField(
        _("Show the announcement"),
        default=False,
        help_text=_("Display the band at the top of every page of the website."),
    )
    message = RichTextField(
        _("Message"),
        blank=True,
        features=["bold", "italic", "link"],
        help_text=_(
            "Keep it short: one or two sentences. Visitors who closed it see it again once you change it."
        ),
    )
    style = models.CharField(
        _("Style"),
        max_length=20,
        choices=AnnouncementStyle.choices,
        default=AnnouncementStyle.INFO,
    )

    panels = [
        FieldPanel("enabled"),
        FieldPanel("message"),
        FieldPanel("style"),
    ]

    class Meta:
        verbose_name = _("Announcement")

    @property
    def is_active(self) -> bool:
        # The editor saves an emptied message as an empty paragraph.
        return self.enabled and bool(strip_tags(self.message).strip())

    @property
    def version(self) -> str:
        """Changes whenever the visible announcement changes."""
        content = f"{self.style}\n{self.message}".encode()
        return hashlib.sha256(content).hexdigest()[:16]
