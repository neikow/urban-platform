from django.utils import timezone
from wagtail.models import Revision

from core.models import User
from legal.models import CodeOfConductConsent, CodeOfConductPage


def has_valid_code_of_conduct_consent(user: User) -> bool:
    last_consent = (
        CodeOfConductConsent.objects.filter(
            user=user,
        )
        .order_by("-consented_at")
        .first()
    )

    if not last_consent or not last_consent.is_up_to_date():
        return False

    return True


def get_latest_code_of_conduct_revision() -> Revision:
    code_of_conduct_page: CodeOfConductPage = CodeOfConductPage.objects.first()
    latest_revision = code_of_conduct_page.revisions.order_by("-created_at").first()
    return latest_revision


def create_code_of_conduct_consent_record(
    user: User, consent_ip: str | None = None
) -> CodeOfConductConsent:
    latest_revision = get_latest_code_of_conduct_revision()

    consent_record = CodeOfConductConsent.objects.create(
        user=user,
        policy_revision=latest_revision,
        consent_ip=consent_ip,
        consented_at=timezone.now(),
    )

    return consent_record
