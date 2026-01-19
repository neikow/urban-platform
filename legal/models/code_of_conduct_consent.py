from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CodeOfConductConsent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_of_conduct_consents",
        verbose_name=_("User"),
    )
    policy_revision = models.ForeignKey(
        "wagtailcore.Revision",
        on_delete=models.PROTECT,
        related_name="code_of_conduct_consents",
        verbose_name=_("Policy Version"),
    )
    consented_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Consented at"),
    )
    consent_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Consent IP Address"),
    )

    class Meta:
        verbose_name = _("Code of Conduct Consent")
        verbose_name_plural = _("Code of Conduct Consents")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "policy_revision"], name="unique_consent_per_version"
            )
        ]

    def is_up_to_date(self) -> bool:
        page = self.policy_revision.content_object
        latest_revision = page.revisions.order_by("-created_at").first()
        return latest_revision == self.policy_revision

    def __str__(self) -> str:
        return f"{self.user} consent to Code Of Conduct ({self.policy_revision.created_at})"
