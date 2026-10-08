from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def give_code_of_conduct_consent(db: None) -> Callable[[Any], Any]:
    """Record a consent to the latest code of conduct revision for a user.

    The code of conduct page is created by a data migration without any
    revision, so one is saved first when needed.
    """
    from legal.models import CodeOfConductPage
    from legal.utils import create_code_of_conduct_consent_record

    def _consent(user: Any) -> Any:
        page = CodeOfConductPage.objects.live().first()
        if page is not None and not page.revisions.exists():
            page.save_revision()
        return create_code_of_conduct_consent_record(user)

    return _consent


@pytest.fixture(autouse=True)
def offline_geocoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never reach the geocoding service: by default it is unavailable.

    Tests about addresses patch ``core.geocoding._fetch`` with canned answers.
    """
    from core import geocoding

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise geocoding.GeocodingUnavailable

    monkeypatch.setattr(geocoding, "_fetch", unavailable)
