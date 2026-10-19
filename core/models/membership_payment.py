from django.db import models
from django.utils.translation import gettext_lazy as _


class MembershipPaymentStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    PAID = "PAID", _("Paid")
    ABANDONED = "ABANDONED", _("Abandoned")


class MembershipPayment(models.Model):
    """A membership paid, or being paid, on HelloAsso (core.helloasso).

    Created when the member leaves for HelloAsso; once HelloAsso confirms the
    payment, the membership is recorded (core.membership_payments). Kept when
    the member deletes their account: it is the association's accounting.
    """

    user = models.ForeignKey(
        "User",
        verbose_name=_("Member"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="membership_payments",
    )
    association = models.ForeignKey(
        "NeighborhoodAssociation",
        verbose_name=_("Neighborhood Association"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    amount_cents = models.PositiveIntegerField(_("Amount (cents)"))
    starts_on = models.DateField(_("Start"))
    ends_on = models.DateField(_("End"))
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=MembershipPaymentStatus.choices,
        default=MembershipPaymentStatus.PENDING,
    )
    checkout_id = models.PositiveIntegerField(
        _("HelloAsso checkout"), null=True, blank=True, unique=True
    )
    order_id = models.PositiveIntegerField(_("HelloAsso order"), null=True, blank=True)
    membership = models.OneToOneField(
        "Membership",
        verbose_name=_("Membership"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment",
    )
    created_at = models.DateTimeField(_("Started on"), auto_now_add=True)
    paid_at = models.DateTimeField(_("Paid on"), null=True, blank=True)

    class Meta:
        verbose_name = _("Membership payment")
        verbose_name_plural = _("Membership payments")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} – {self.amount_cents / 100:.2f} € ({self.get_status_display()})"

    @property
    def amount(self) -> float:
        return self.amount_cents / 100
