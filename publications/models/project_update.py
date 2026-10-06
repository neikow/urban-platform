from datetime import date

from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel
from wagtail.models import Orderable


class ProjectUpdate(Orderable):
    """A dated step in a project's life, shown in its public timeline.

    When the page is published, new updates with `notify_participants` are
    emailed once to voters and idea contributors who opted in.
    """

    page = ParentalKey(
        "publications.ProjectPage",
        on_delete=models.CASCADE,
        related_name="updates",
    )
    date: models.DateField[date, date] = models.DateField(_("Date"), default=date.today)
    title: models.CharField[str, str] = models.CharField(_("Title"), max_length=200)
    body: models.TextField[str, str] = models.TextField(_("Text"), max_length=3000)
    notify_participants: models.BooleanField[bool, bool] = models.BooleanField(
        _("Email participants"),
        default=True,
        help_text=_(
            "Sent once, when the page is published, to people who voted or shared an "
            "idea and asked for project updates. Untick for past events you are adding "
            "to the timeline."
        ),
    )

    panels = [
        FieldPanel("date"),
        FieldPanel("title"),
        FieldPanel("body"),
        FieldPanel("notify_participants"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = _("Project update")
        verbose_name_plural = _("Project updates")

    def __str__(self) -> str:
        return self.title
