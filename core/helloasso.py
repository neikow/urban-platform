"""HelloAsso Checkout: memberships are paid on HelloAsso, to the Fédération's account.

The site creates a checkout intent and sends the member to its page. Once they
paid, HelloAsso sends them back (returnUrl) and notifies the site (webhook).
Neither is trusted: the payment is read again from the API (``get_checkout``).

Settings (environment): HELLOASSO_CLIENT_ID, HELLOASSO_CLIENT_SECRET,
HELLOASSO_ORGANIZATION_SLUG, and HELLOASSO_API_URL for the sandbox
(https://api.helloasso-sandbox.com). The API key needs the Checkout privilege.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
TOKEN_CACHE_KEY = "helloasso:access_token"  # nosec B105: a cache key, not a secret
# Payment states that mean the money is collected (or about to be, for SEPA).
PAID_STATES = {"Authorized", "Registered"}


class HelloAssoError(Exception):
    """HelloAsso could not be reached, or refused the request."""

    def __init__(self, message: str, status: int | None = None, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def is_configured() -> bool:
    return bool(
        settings.HELLOASSO_CLIENT_ID
        and settings.HELLOASSO_CLIENT_SECRET
        and settings.HELLOASSO_ORGANIZATION_SLUG
    )


def _request(method: str, path: str, data: bytes | None, headers: dict[str, str]) -> dict[str, Any]:
    url = settings.HELLOASSO_API_URL.rstrip("/") + path
    request = Request(
        url, data=data, method=method, headers={"Accept": "application/json", **headers}
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310: https URL from settings
            return json.load(response)
    except HTTPError as error:
        try:
            body = json.load(error)
        except ValueError:
            body = None
        logger.warning("HelloAsso %s %s answered %s: %s", method, path, error.code, body)
        raise HelloAssoError(f"HelloAsso answered {error.code}", error.code, body) from error
    except (URLError, TimeoutError, ValueError) as error:
        logger.warning("HelloAsso %s %s failed: %s", method, path, error)
        raise HelloAssoError("HelloAsso is unreachable") from error


def access_token() -> str:
    """A bearer token, kept until shortly before it expires."""
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token
    data = _request(
        "POST",
        "/oauth2/token",
        urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": settings.HELLOASSO_CLIENT_ID,
                "client_secret": settings.HELLOASSO_CLIENT_SECRET,
            }
        ).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = data["access_token"]
    lifetime = int(data.get("expires_in") or 1800)
    cache.set(TOKEN_CACHE_KEY, token, max(lifetime - 60, 60))
    return token


def _api(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    slug = quote(settings.HELLOASSO_ORGANIZATION_SLUG, safe="")
    headers = {"Authorization": f"Bearer {access_token()}"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    return _request(method, f"/v5/organizations/{slug}{path}", data, headers)


@dataclass(frozen=True)
class Checkout:
    id: int
    redirect_url: str


def create_checkout(
    *,
    amount_cents: int,
    item_name: str,
    payer: dict[str, str],
    return_url: str,
    error_url: str,
    back_url: str,
    metadata: dict[str, Any],
) -> Checkout:
    """A checkout intent; its page (redirect_url) expires after 15 minutes."""
    data = _api(
        "POST",
        "/checkout-intents",
        {
            "totalAmount": amount_cents,
            "initialAmount": amount_cents,
            "itemName": item_name[:250],
            "backUrl": back_url,
            "errorUrl": error_url,
            "returnUrl": return_url,
            "containsDonation": False,
            "payer": payer,
            "metadata": metadata,
        },
    )
    return Checkout(id=int(data["id"]), redirect_url=data["redirectUrl"])


@dataclass(frozen=True)
class CheckoutState:
    order_id: int | None
    paid_cents: int

    @property
    def is_paid(self) -> bool:
        return self.order_id is not None and self.paid_cents > 0


def get_checkout(checkout_id: int) -> CheckoutState:
    """What was paid for a checkout intent: HelloAsso adds the order once paid."""
    data = _api("GET", f"/checkout-intents/{int(checkout_id)}")
    order = data.get("order") or {}
    payments = order.get("payments") or []
    paid = sum(int(p.get("amount") or 0) for p in payments if p.get("state") in PAID_STATES)
    return CheckoutState(order_id=order.get("id"), paid_cents=paid)
