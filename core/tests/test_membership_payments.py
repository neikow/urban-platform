"""Joining online: calendar-year periods, the grace month, HelloAsso payments."""

import io
import json
from datetime import date, datetime, timedelta
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from core import helloasso
from core.helloasso import CheckoutState, HelloAssoError
from core.membership_payments import check_pending_payments, start_payment, sync_payment
from core.models import (
    Membership,
    MembershipPayment,
    MembershipPaymentStatus,
    NeighborhoodAssociation,
    User,
    UserRole,
)
from core.models.membership import may_join, membership_period

HELLOASSO = {
    "HELLOASSO_API_URL": "https://api.helloasso.test",
    "HELLOASSO_CLIENT_ID": "client",
    "HELLOASSO_CLIENT_SECRET": "secret",
    "HELLOASSO_ORGANIZATION_SLUG": "federation-des-ciq",
    "MEMBERSHIP_FEE_CENTS": 1000,
    "WAGTAILADMIN_BASE_URL": "https://urba7.example",
}
SEAT = {"type": "Point", "coordinates": [5.35, 43.285]}


@pytest.fixture(autouse=True)
def helloasso_settings():
    cache.delete(helloasso.TOKEN_CACHE_KEY)
    with override_settings(**HELLOASSO):
        yield


@pytest.fixture
def resident(db):
    return User.objects.create_user(
        email="resident@example.com", password="Password123", first_name="Marie", last_name="Durand"
    )


@pytest.fixture
def ciq(db):
    return NeighborhoodAssociation.objects.create(
        name="Vallon des Auffes", code="702", address_location=SEAT
    )


@pytest.fixture
def no_email():
    with patch("core.emails.tasks.send_membership_email.delay") as delay:
        yield delay


def on(day: date):
    """Freeze timezone.localdate (and now) on a day."""
    moment = timezone.make_aware(datetime(day.year, day.month, day.day, 12))
    return patch.multiple(
        "django.utils.timezone", localdate=lambda *a, **k: day, now=lambda: moment
    )


def member(user: User, starts: date, ends: date | None) -> Membership:
    return Membership.objects.create(user=user, starts_on=starts, ends_on=ends)


# --- periods ------------------------------------------------------------------


@pytest.mark.django_db
class TestMembershipPeriod:
    def test_joining_during_the_year(self, resident):
        assert membership_period(resident.memberships.all(), date(2026, 3, 10)) == (
            date(2026, 3, 10),
            date(2026, 12, 31),
        )

    def test_joining_in_december_covers_the_next_year(self, resident):
        assert membership_period(resident.memberships.all(), date(2026, 12, 5)) == (
            date(2026, 12, 5),
            date(2027, 12, 31),
        )

    def test_renewing_in_december_starts_on_january_first(self, resident):
        member(resident, date(2026, 3, 10), date(2026, 12, 31))

        assert membership_period(resident.memberships.all(), date(2026, 12, 15)) == (
            date(2027, 1, 1),
            date(2027, 12, 31),
        )

    def test_renewing_in_the_grace_month(self, resident):
        member(resident, date(2026, 3, 10), date(2026, 12, 31))

        assert membership_period(resident.memberships.all(), date(2027, 1, 20)) == (
            date(2027, 1, 20),
            date(2027, 12, 31),
        )


@pytest.mark.django_db
class TestMayJoin:
    def test_not_a_member(self, resident):
        assert may_join(resident.memberships.all(), date(2026, 6, 1))

    def test_member_for_this_year(self, resident):
        member(resident, date(2026, 3, 10), date(2026, 12, 31))

        assert not may_join(resident.memberships.all(), date(2026, 6, 1))
        assert may_join(resident.memberships.all(), date(2026, 12, 1))
        assert may_join(resident.memberships.all(), date(2027, 1, 10))

    def test_already_renewed(self, resident):
        member(resident, date(2026, 3, 10), date(2026, 12, 31))
        member(resident, date(2027, 1, 1), date(2027, 12, 31))

        assert not may_join(resident.memberships.all(), date(2026, 12, 20))

    def test_open_ended_membership(self, resident):
        member(resident, date(2020, 1, 1), None)

        assert not may_join(resident.memberships.all(), date(2026, 12, 20))


@pytest.mark.django_db
class TestGraceMonth:
    def test_members_keep_their_rights_for_a_month(self, resident):
        today = timezone.localdate()
        member(resident, today - timedelta(days=300), today - timedelta(days=20))

        assert resident.is_member
        assert not Membership.objects.active().exists()
        assert resident.current_membership is not None

    def test_after_the_grace_month(self, resident):
        today = timezone.localdate()
        member(resident, today - timedelta(days=300), today - timedelta(days=40))

        assert not resident.is_member
        assert resident.current_membership is None

    def test_current_membership_is_the_longest(self, resident):
        today = timezone.localdate()
        member(resident, today - timedelta(days=10), today + timedelta(days=10))
        longest = member(resident, today - timedelta(days=5), today + timedelta(days=300))

        assert resident.current_membership == longest


# --- HelloAsso client ----------------------------------------------------------


def respond(*bodies):
    """Stand-in for urlopen answering the given JSON bodies in turn; records the requests."""
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        body = bodies[len(requests) - 1]
        if isinstance(body, Exception):
            raise body
        return io.BytesIO(json.dumps(body).encode())

    return fake_urlopen, requests


TOKEN = {"access_token": "jwt", "refresh_token": "r", "token_type": "bearer", "expires_in": "1800"}


class TestHelloAssoClient:
    def test_creates_a_checkout(self, db):
        fake, requests = respond(TOKEN, {"id": 42, "redirectUrl": "https://helloasso.test/pay/42"})
        with patch("core.helloasso.urlopen", fake):
            checkout = helloasso.create_checkout(
                amount_cents=1000,
                item_name="Adhésion",
                payer={"firstName": "Marie", "lastName": "Durand", "email": "m@example.com"},
                return_url="https://urba7.example/adhesion/retour/?type=return",
                error_url="https://urba7.example/adhesion/retour/?type=error",
                back_url="https://urba7.example/adhesion/",
                metadata={"payment": 1},
            )

        assert checkout == helloasso.Checkout(id=42, redirect_url="https://helloasso.test/pay/42")
        token_request, checkout_request = requests
        assert token_request.full_url == "https://api.helloasso.test/oauth2/token"
        assert b"grant_type=client_credentials" in token_request.data
        assert checkout_request.full_url == (
            "https://api.helloasso.test/v5/organizations/federation-des-ciq/checkout-intents"
        )
        assert checkout_request.get_header("Authorization") == "Bearer jwt"
        payload = json.loads(checkout_request.data)
        assert payload["totalAmount"] == payload["initialAmount"] == 1000
        assert payload["containsDonation"] is False
        assert payload["metadata"] == {"payment": 1}

    def test_token_is_reused(self, db):
        fake, requests = respond(TOKEN, {"id": 1}, {"id": 1})
        locmem = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
        with override_settings(CACHES=locmem), patch("core.helloasso.urlopen", fake):
            helloasso.get_checkout(1)
            helloasso.get_checkout(1)

        assert len(requests) == 3

    def test_reads_what_was_paid(self, db):
        intent = {
            "id": 42,
            "order": {
                "id": 7,
                "payments": [
                    {"amount": 1000, "state": "Authorized"},
                    {"amount": 500, "state": "Refused"},
                ],
            },
        }
        fake, _ = respond(TOKEN, intent)
        with patch("core.helloasso.urlopen", fake):
            state = helloasso.get_checkout(42)

        assert state == CheckoutState(order_id=7, paid_cents=1000)
        assert state.is_paid

    def test_no_order_yet(self, db):
        fake, _ = respond(TOKEN, {"id": 42, "redirectUrl": "https://helloasso.test/pay/42"})
        with patch("core.helloasso.urlopen", fake):
            assert not helloasso.get_checkout(42).is_paid

    def test_refusals_keep_the_status(self, db):
        error = HTTPError("u", 400, "Bad Request", {}, io.BytesIO(b'{"errors": ["payer"]}'))  # type: ignore[arg-type]
        fake, _ = respond(TOKEN, error)
        with patch("core.helloasso.urlopen", fake), pytest.raises(HelloAssoError) as raised:
            helloasso.get_checkout(42)

        assert raised.value.status == 400
        assert raised.value.body == {"errors": ["payer"]}

    def test_configuration(self):
        assert helloasso.is_configured()
        with override_settings(HELLOASSO_CLIENT_ID=""):
            assert not helloasso.is_configured()


# --- payments -----------------------------------------------------------------


def checkout(redirect: str = "https://helloasso.test/pay/42", checkout_id: int = 42):
    return patch(
        "core.helloasso.create_checkout",
        return_value=helloasso.Checkout(id=checkout_id, redirect_url=redirect),
    )


def paid(cents: int = 1000, order: int | None = 7):
    return patch(
        "core.helloasso.get_checkout", return_value=CheckoutState(order_id=order, paid_cents=cents)
    )


def pending_payment(user: User, ciq=None, checkout_id: int = 42) -> MembershipPayment:
    return MembershipPayment.objects.create(
        user=user,
        association=ciq,
        amount_cents=1000,
        starts_on=date(2026, 3, 10),
        ends_on=date(2026, 12, 31),
        checkout_id=checkout_id,
    )


@pytest.mark.django_db
class TestPayments:
    def test_start_payment(self, resident, ciq):
        resident.association = ciq
        with on(date(2026, 3, 10)), checkout() as create:
            url = start_payment(resident)

        assert url == "https://helloasso.test/pay/42"
        payment = MembershipPayment.objects.get()
        assert payment.status == MembershipPaymentStatus.PENDING
        assert (payment.checkout_id, payment.association) == (42, ciq)
        assert (payment.starts_on, payment.ends_on) == (date(2026, 3, 10), date(2026, 12, 31))
        kwargs = create.call_args.kwargs
        assert kwargs["amount_cents"] == 1000
        assert kwargs["metadata"]["payment"] == payment.pk
        assert kwargs["return_url"] == "https://urba7.example/adhesion/retour/?type=return"
        assert kwargs["payer"]["email"] == "resident@example.com"
        assert "Vallon des Auffes" in kwargs["item_name"]

    def test_paid_payment_records_the_membership_once(
        self, resident, ciq, no_email, django_capture_on_commit_callbacks
    ):
        payment = pending_payment(resident, ciq)

        with paid(), django_capture_on_commit_callbacks(execute=True):
            assert sync_payment(payment)
            assert sync_payment(payment)
            payment.refresh_from_db()
            assert sync_payment(payment)

        membership = Membership.objects.get()
        assert (membership.user, membership.association) == (resident, ciq)
        assert (membership.starts_on, membership.ends_on) == (date(2026, 3, 10), date(2026, 12, 31))
        assert payment.status == MembershipPaymentStatus.PAID
        assert (payment.order_id, payment.membership) == (7, membership)
        no_email.assert_called_once()
        assert no_email.call_args.args[:2] == (resident.pk, "confirmation")

    def test_not_paid_yet(self, resident):
        payment = pending_payment(resident)

        with paid(cents=0, order=None):
            assert not sync_payment(payment)

        assert not Membership.objects.exists()

    def test_underpaid(self, resident):
        payment = pending_payment(resident)

        with paid(cents=500):
            assert not sync_payment(payment)

        assert not Membership.objects.exists()

    def test_check_pending_payments(self, resident, no_email):
        recent = pending_payment(resident, checkout_id=1)
        old = pending_payment(resident, checkout_id=2)
        MembershipPayment.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=1)
        )

        with paid(cents=0, order=None):
            assert check_pending_payments() == 0

        recent.refresh_from_db()
        old.refresh_from_db()
        assert recent.status == MembershipPaymentStatus.PENDING
        assert old.status == MembershipPaymentStatus.ABANDONED

    def test_late_payment_of_an_abandoned_checkout(self, resident, no_email):
        payment = pending_payment(resident)
        payment.status = MembershipPaymentStatus.ABANDONED
        payment.save()

        with paid():
            assert sync_payment(payment)

        assert Membership.objects.filter(user=resident).exists()


# --- pages --------------------------------------------------------------------


@pytest.mark.django_db
class TestMembershipPage:
    def test_visitors_are_invited_to_create_an_account(self, client):
        content = client.get(reverse("membership")).content.decode()

        assert f"{reverse('register')}?next={reverse('membership')}" in content
        assert f'action="{reverse("membership")}"' not in content

    def test_form_for_residents(self, client, resident, ciq):
        client.force_login(resident)

        response = client.get(reverse("membership"))

        assert response.context["may_join"]
        assert "<association-select" in response.content.decode()

    def test_paying_redirects_to_helloasso(self, client, resident, ciq):
        client.force_login(resident)

        with checkout():
            response = client.post(
                reverse("membership"), {"address": "Vallon des Auffes", "association": ciq.pk}
            )

        assert response.status_code == 302
        assert response["Location"] == "https://helloasso.test/pay/42"
        resident.refresh_from_db()
        assert resident.association == ciq
        assert MembershipPayment.objects.get().association == ciq

    def test_a_ciq_is_needed(self, client, resident):
        client.force_login(resident)

        with checkout() as create:
            response = client.post(reverse("membership"), {"address": "Somewhere"})

        assert response.status_code == 200
        assert "association" in response.context["form"].errors
        create.assert_not_called()

    def test_payments_not_open(self, client, resident, ciq):
        client.force_login(resident)

        with override_settings(HELLOASSO_CLIENT_ID=""), checkout() as create:
            response = client.post(
                reverse("membership"), {"address": "Vallon des Auffes", "association": ciq.pk}
            )

        assert response.status_code == 200
        assert response.context["form"].non_field_errors()
        create.assert_not_called()

    def test_helloasso_refuses(self, client, resident, ciq):
        client.force_login(resident)

        with patch("core.helloasso.create_checkout", side_effect=HelloAssoError("no", 400)):
            response = client.post(
                reverse("membership"), {"address": "Vallon des Auffes", "association": ciq.pk}
            )

        assert response.status_code == 200
        assert response.context["form"].non_field_errors()

    def test_members_do_not_pay_twice(self, client, resident, ciq):
        today = timezone.localdate()
        if today.month == 12:
            pytest.skip("December opens the renewals")
        member(resident, today - timedelta(days=10), date(today.year, 12, 31))
        client.force_login(resident)

        with checkout() as create:
            response = client.post(
                reverse("membership"), {"address": "Vallon des Auffes", "association": ciq.pk}
            )

        assert response.status_code == 302
        assert response["Location"] == reverse("membership")
        create.assert_not_called()

    def test_profile_links_to_the_membership(self, client, resident):
        client.force_login(resident)

        assert reverse("membership") in client.get(reverse("me")).content.decode()


@pytest.mark.django_db
class TestReturnFromHelloAsso:
    def test_paid(self, client, resident, no_email):
        pending_payment(resident)
        client.force_login(resident)

        with paid():
            response = client.get(
                reverse("membership_return"),
                {"type": "return", "checkoutIntentId": "42", "code": "succeeded", "orderId": "7"},
            )

        assert response["Location"] == reverse("membership")
        assert Membership.objects.filter(user=resident).exists()

    def test_the_return_url_alone_proves_nothing(self, client, resident):
        pending_payment(resident)
        client.force_login(resident)

        with paid(cents=0, order=None):
            client.get(
                reverse("membership_return"),
                {"type": "return", "checkoutIntentId": "42", "code": "succeeded"},
            )

        assert not Membership.objects.exists()

    def test_someone_elses_checkout(self, client, resident):
        other = User.objects.create_user(email="other@example.com", password="Password123")
        pending_payment(other)
        client.force_login(resident)

        with paid() as get:
            client.get(reverse("membership_return"), {"checkoutIntentId": "42"})

        get.assert_not_called()
        assert not Membership.objects.exists()

    def test_login_required(self, client):
        response = client.get(reverse("membership_return"), {"checkoutIntentId": "42"})

        assert response.status_code == 302
        assert reverse("membership_return") not in response["Location"].split("?")[0]


@pytest.mark.django_db
class TestHelloAssoNotification:
    def post(self, client, body):
        return client.post(
            reverse("helloasso_notification"),
            data=body if isinstance(body, str) else json.dumps(body),
            content_type="application/json",
        )

    def test_order_notification(self, client, resident, no_email):
        payment = pending_payment(resident)

        with paid():
            response = self.post(
                client,
                {"eventType": "Order", "data": {"id": 7}, "metadata": {"payment": payment.pk}},
            )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == MembershipPaymentStatus.PAID

    def test_found_by_checkout_id(self, client, resident, no_email):
        payment = pending_payment(resident)

        with paid():
            self.post(client, {"eventType": "Payment", "data": {"checkoutIntentId": 42}})

        payment.refresh_from_db()
        assert payment.status == MembershipPaymentStatus.PAID

    def test_unknown_payment(self, client, db):
        with paid() as get:
            response = self.post(client, {"eventType": "Form", "data": {}})

        assert response.status_code == 200
        get.assert_not_called()

    def test_invalid_body(self, client, db):
        assert self.post(client, "not json").status_code == 400
        assert self.post(client, "[1]").status_code == 400

    def test_helloasso_down_asks_for_a_retry(self, client, resident):
        payment = pending_payment(resident)

        with patch("core.helloasso.get_checkout", side_effect=HelloAssoError("down")):
            response = self.post(client, {"metadata": {"payment": payment.pk}})

        assert response.status_code == 503


@pytest.mark.django_db
class TestPaymentsAdmin:
    def test_administrators_see_payments_read_only(self, client, resident):
        admin = User.objects.create_user(
            email="admin@example.com", password="Password123", role=UserRole.ADMIN
        )
        pending_payment(resident)
        client.force_login(admin)

        assert client.get(reverse("membership_payment:index")).status_code == 200
        assert client.get(reverse("membership_payment:add")).status_code in (302, 403)

    def test_moderators_do_not(self, client, db):
        moderator = User.objects.create_user(
            email="moderator@example.com", password="Password123", role=UserRole.MODERATOR
        )
        client.force_login(moderator)

        assert client.get(reverse("membership_payment:index")).status_code in (302, 403)
