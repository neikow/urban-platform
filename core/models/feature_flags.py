from typing import Any

from django.db import models
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


@register_setting(icon="cogs")
class FeatureFlags(BaseGenericSetting):
    """Features turned on or off from the admin, without a deployment."""

    participation_requires_subscription = models.BooleanField(
        _("Reserve participation to subscribers"),
        default=False,
        help_text=_(
            "Only subscribers may vote and share ideas. Turn on once subscribing is "
            "possible: other users will be invited to subscribe."
        ),
    )

    panels = [FieldPanel("participation_requires_subscription")]

    class Meta:
        verbose_name = _("Features")


def participation_open_to(user: Any, request: HttpRequest | None = None) -> bool:
    """Whether the user may vote and share ideas, as far as subscription goes.

    The other conditions (a verified email, the code of conduct) are checked apart.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_subscriber", False):
        return True
    return not FeatureFlags.load(request_or_site=request).participation_requires_subscription
