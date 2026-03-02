from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class VoteChoice(models.TextChoices):
    UNFAVORABLE = "UNFAVORABLE", _("Unfavorable")
    RATHER_UNFAVORABLE = "RATHER_UNFAVORABLE", _("Rather Unfavorable")
    RATHER_FAVORABLE = "RATHER_FAVORABLE", _("Rather Favorable")
    FAVORABLE = "FAVORABLE", _("Favorable")


# Shared constants for grouping vote choices
FAVORABLE_CHOICES = (VoteChoice.FAVORABLE, VoteChoice.RATHER_FAVORABLE)
UNFAVORABLE_CHOICES = (VoteChoice.UNFAVORABLE, VoteChoice.RATHER_UNFAVORABLE)

# Value-based versions for use in queryset filters
FAVORABLE_VALUES = tuple(choice.value for choice in FAVORABLE_CHOICES)
UNFAVORABLE_VALUES = tuple(choice.value for choice in UNFAVORABLE_CHOICES)


class FormResponse(models.Model):
    """
    Represents a user's vote response on a project.
    Each user can only have one response per project.
    """

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="form_responses",
        verbose_name=_("User"),
    )
    project = models.ForeignKey(
        "publications.ProjectPage",
        on_delete=models.CASCADE,
        related_name="vote_responses",
        verbose_name=_("Project"),
    )
    choice = models.CharField(
        _("Choice"),
        max_length=30,
        choices=VoteChoice.choices,
    )
    comment = models.TextField(
        _("Comment"),
        blank=True,
        help_text=_("Optional comment to explain your vote"),
    )
    anonymize = models.BooleanField(
        _("Anonymize"),
        default=False,
        help_text=_("Hide your identity in public displays"),
    )

    class Meta:
        verbose_name = _("Vote Response")
        verbose_name_plural = _("Vote Responses")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                name="unique_user_project_vote",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.project.title} - {self.choice}"
