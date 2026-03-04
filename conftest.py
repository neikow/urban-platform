from typing import Generator

import pytest
from django.utils import translation


@pytest.fixture(autouse=True)
def force_locale() -> Generator[None, None, None]:
    translation.activate("fr")
    yield
    translation.deactivate()
