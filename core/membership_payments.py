"""Joining online: a membership paid on HelloAsso becomes a Membership.

``start_payment`` records a pending MembershipPayment and creates the HelloAsso
checkout. ``sync_payment`` reads the checkout back from HelloAsso, after the
member's return, a HelloAsso notification or the periodic check, and records
the membership once paid: whichever comes first, it is recorded once.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from core import helloasso
from core.audit import audit
from core.models import Membership, MembershipPayment, MembershipPaymentStatus, User
from core.models.membership import membership_period

logger = logging.getLogger(__name__)

# HelloAsso's advice: a checkout with no payment after 45 minutes is abandoned.
ABANDONED_AFTER = timedelta(minutes=45)
# Pending payments older than this are no longer asked about.
GIVE_UP_AFTER = timedelta(days=2)


def absolute_url(path: str) -> str:
    return f"{settings.WAGTAILADMIN_BASE_URL.rstrip('/')}{path}"


def start_payment(user: User) -> str:
    """Record a pending payment for the next membership period; returns the HelloAsso page.

    Raises helloasso.HelloAssoError when HelloAsso refuses or cannot be reached.
    """
    starts, ends = membership_period(user.memberships.all())
    payment = MembershipPayment.objects.create(
        user=user,
        association=user.association,
        amount_cents=settings.MEMBERSHIP_FEE_CENTS,
        starts_on=starts,
        ends_on=ends,
    )
    return_url = absolute_url(reverse("membership_return"))
    item = f"Adhésion {settings.WEBSITE_NAME} {ends.year}"
    if user.association:
        item = f"{item} – CIQ {user.association.name}"
    checkout = helloasso.create_checkout(
        amount_cents=payment.amount_cents,
        item_name=item,
        payer={"firstName": user.first_name, "lastName": user.last_name, "email": user.email},
        return_url=f"{return_url}?type=return",
        error_url=f"{return_url}?type=error",
        back_url=absolute_url(reverse("membership")),
        metadata={"payment": payment.pk, "user": str(user.uuid)},
    )
    payment.checkout_id = checkout.id
    payment.save(update_fields=["checkout_id"])
    audit(user, "core.membership.payment_start", user=user, amount=payment.amount_cents)
    return checkout.redirect_url


def sync_payment(payment: MembershipPayment) -> bool:
    """Ask HelloAsso whether the payment went through; record the membership if so.

    Returns whether the payment is paid. Raises helloasso.HelloAssoError.
    """
    if payment.status == MembershipPaymentStatus.PAID:
        return True
    if payment.checkout_id is None:
        return False
    state = helloasso.get_checkout(payment.checkout_id)
    if not state.is_paid:
        return False
    if state.paid_cents < payment.amount_cents:
        logger.error(
            "Checkout %s paid %s cents instead of %s",
            payment.checkout_id,
            state.paid_cents,
            payment.amount_cents,
        )
        return False
    return record_membership(payment.pk, state.order_id)


def record_membership(payment_id: int, order_id: int | None) -> bool:
    """Turn a paid payment into a membership, once."""
    from core.emails.tasks import send_membership_email

    with transaction.atomic():
        payment = MembershipPayment.objects.select_for_update().get(pk=payment_id)
        if payment.status == MembershipPaymentStatus.PAID:
            return True
        payment.status = MembershipPaymentStatus.PAID
        payment.order_id = order_id
        payment.paid_at = timezone.now()
        if payment.user is not None:
            payment.membership = Membership.objects.create(
                user=payment.user,
                association=payment.association,
                starts_on=payment.starts_on,
                ends_on=payment.ends_on,
                note=f"HelloAsso, commande {order_id}",
            )
        payment.save()
        if payment.user is not None:
            user = payment.user
            audit(user, "core.membership.paid", user=user, order=order_id)
            context = {
                "ends_on": date_format(payment.ends_on, "j F Y"),
                "association": payment.association.name if payment.association else None,
            }
            transaction.on_commit(
                lambda: send_membership_email.delay(user.pk, "confirmation", context)  # type: ignore[attr-defined]
            )
    return True


def payment_from_notification(body: dict) -> MembershipPayment | None:
    """The payment a HelloAsso notification is about, by our metadata or the checkout id."""
    metadata = body.get("metadata") or {}
    data = body.get("data") or {}
    if isinstance(metadata, dict) and str(metadata.get("payment", "")).isdigit():
        payment = MembershipPayment.objects.filter(pk=int(metadata["payment"])).first()
        if payment:
            return payment
    checkout_id = data.get("checkoutIntentId") if isinstance(data, dict) else None
    if isinstance(data, dict) and not checkout_id:
        checkout_id = (data.get("order") or {}).get("checkoutIntentId")
    if isinstance(checkout_id, (int, str)) and str(checkout_id).isdigit():
        return MembershipPayment.objects.filter(checkout_id=int(checkout_id)).first()
    return None


def check_pending_payments() -> int:
    """Catch payments whose notification was lost; give up on abandoned ones. Returns the paid."""
    now = timezone.now()
    pending = MembershipPayment.objects.filter(
        status=MembershipPaymentStatus.PENDING, created_at__gte=now - GIVE_UP_AFTER
    )
    paid = 0
    for payment in pending:
        try:
            if sync_payment(payment):
                paid += 1
                continue
        except helloasso.HelloAssoError:
            continue
        if payment.created_at < now - ABANDONED_AFTER:
            payment.status = MembershipPaymentStatus.ABANDONED
            payment.save(update_fields=["status"])
    MembershipPayment.objects.filter(
        status=MembershipPaymentStatus.PENDING, created_at__lt=now - GIVE_UP_AFTER
    ).update(status=MembershipPaymentStatus.ABANDONED)
    return paid
