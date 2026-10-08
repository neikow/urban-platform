"""Setting up a new website of the platform, then keeping it in line (``bootstrap_tenant``).

Every website runs the same image, described by environment variables (see
"Deploying a website" in the README). After the migrations, the bootstrap brings the database
in line with them. Each step is idempotent, so it runs at every deployment:

- the Wagtail site answers on BASE_URL;
- TENANT_ADMIN_EMAIL has an administrator account, invited to set a password;
- the territory is TENANT_TERRITORY (an INSEE code), fetched again if it changed;
- the contact email is TENANT_CONTACT_EMAIL, until an administrator changes it;
- the pages left empty by the migrations get their starter content.

Nothing the association edited is overwritten: the steps only fill what is
missing, except the territory, which the platform owns.
"""

import logging
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from django.db import transaction
from wagtail.models import Page, Site

logger = logging.getLogger(__name__)

# Pages created empty by the migrations, and the template that fills them.
STARTER_PAGES = (
    ("home.HomePage", "participation"),
    ("about.AboutWebsitePage", "presentation"),
    ("about.AboutCommissionPage", "presentation"),
)
# The association's page was created for the first website, with its name.
LEGACY_ASSOCIATION_TITLE = "La commission urbanisme"
ASSOCIATION_TITLE = "L'association"
ASSOCIATION_SLUG = "association"


@dataclass
class TenantConfig:
    base_url: str = ""
    admin_email: str = ""
    territory: str = ""
    contact_email: str = ""

    @classmethod
    def from_environment(cls, environ: dict[str, str]) -> "TenantConfig":
        return cls(
            base_url=environ.get("BASE_URL", "").strip(),
            admin_email=environ.get("TENANT_ADMIN_EMAIL", "").strip().lower(),
            territory=environ.get("TENANT_TERRITORY", "").strip(),
            contact_email=environ.get("TENANT_CONTACT_EMAIL", "").strip(),
        )


@dataclass
class Report:
    """What the bootstrap did, and what it could not do (the next run retries)."""

    done: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def configure_site(base_url: str, report: Report) -> None:
    """The default Wagtail site answers on BASE_URL: page URLs and emails use it."""
    if not base_url:
        return
    parts = urlsplit(base_url)
    if not parts.hostname:
        report.warnings.append(f"BASE_URL is not a URL: {base_url!r}.")
        return
    port = parts.port or (443 if parts.scheme == "https" else 80)
    site = Site.objects.filter(is_default_site=True).first()
    if site is None:
        report.warnings.append("No default Wagtail site.")
        return
    if (site.hostname, site.port) != (parts.hostname, port):
        site.hostname, site.port = parts.hostname, port
        site.save()
        report.done.append(f"Site: {parts.hostname}:{port}.")


def ensure_admin(email: str, report: Report) -> None:
    """An administrator account for ``email``, invited to choose a password.

    Existing accounts are left as they are: the bootstrap never changes a role.
    """
    from core.emails.tasks import send_password_reset_email
    from core.models import User, UserRole

    if not email or User.objects.with_deleted().filter(email=email).exists():
        return
    user = User.objects.create_user(
        email=email,
        password=None,
        role=UserRole.ADMIN,
        is_superuser=True,
        is_verified=True,
    )
    report.done.append(f"Administrator: {email}.")
    # The password reset email doubles as the invitation.
    transaction.on_commit(lambda: send_password_reset_email.delay(user.pk))  # type: ignore[attr-defined]


def ensure_territory(code: str, report: Report) -> None:
    """The territory of TENANT_TERRITORY, fetched when it is new or changed."""
    from core import territories
    from core.models import Territory

    if not code or Territory.current().code == code:
        return
    try:
        changed = territories.apply(territories.fetch(code))
    except territories.TerritoryUnavailable as error:
        report.warnings.append(f"Territory {code} not set: {error}")
        return
    report.done.append(f"Territory: {Territory.current().name} ({code}).")
    if changed:
        from publications.map_tiles import queue_refresh

        transaction.on_commit(queue_refresh)


def ensure_contact(email: str, report: Report) -> None:
    """The contact email, unless the association already set one."""
    from core import branding

    current = branding.current()
    if email and not current.contact_email:
        current.contact_email = email
        current.save()
        report.done.append(f"Contact: {email}.")


def _is_empty(page: Page) -> bool:
    return not page.content and not page.has_unpublished_changes  # type: ignore[attr-defined]


def seed_pages(report: Report) -> None:
    """Starter content in the pages the migrations left empty, published."""
    import json

    from django.apps import apps

    from core.page_templates import get_template

    for model_label, slug in STARTER_PAGES:
        model = apps.get_model(model_label)
        template = get_template(model, slug)
        page = model.objects.first()
        if page is None or template is None or not _is_empty(page):
            continue
        page.content = json.dumps(template.content())
        if page.title == LEGACY_ASSOCIATION_TITLE:
            page.title, page.draft_title, page.slug = (
                ASSOCIATION_TITLE,
                ASSOCIATION_TITLE,
                ASSOCIATION_SLUG,
            )
        page.save_revision().publish()
        report.done.append(f"Starter content: {page.title}.")


def bootstrap(config: TenantConfig) -> Report:
    report = Report()
    with transaction.atomic():
        configure_site(config.base_url, report)
        ensure_admin(config.admin_email, report)
        ensure_territory(config.territory, report)
        ensure_contact(config.contact_email, report)
        # Last: the starter texts name the territory and the contact.
        seed_pages(report)
    return report
