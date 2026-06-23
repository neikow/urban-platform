from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class IdeaResponse(models.Model):
    """An idea a resident proposes on a project that collects ideas.

    Stored separately from :class:`~publications.models.form.FormResponse`
    (votes) so switching a project between voting and idea collection never
    destroys the responses gathered for the other mode. Each user keeps a
    single, editable idea per project, mirroring the voting flow.
    """

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idea_responses",
        verbose_name=_("User"),
    )
    project = models.ForeignKey(
        "publications.ProjectPage",
        on_delete=models.CASCADE,
        related_name="idea_responses",
        verbose_name=_("Project"),
    )
    description = models.TextField(
        _("Idea"),
        help_text=_("Describe your idea or alternative proposal for this project"),
    )
    anonymize = models.BooleanField(
        _("Anonymize"),
        default=False,
        help_text=_("Hide your identity in administrator displays"),
    )

    class Meta:
        verbose_name = _("Idea Response")
        verbose_name_plural = _("Idea Responses")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                name="unique_user_project_idea",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.project.title} - idea"
