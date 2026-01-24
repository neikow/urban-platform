import pytest
from django.test import RequestFactory
from core.utils import get_client_ip


@pytest.fixture
def request_factory():
    return RequestFactory()


def test_get_client_ip_x_forwarded_for(request_factory: RequestFactory) -> None:
    request = request_factory.get("/", HTTP_X_FORWARDED_FOR="192.168.1.1")
    assert get_client_ip(request) == "192.168.1.1"


def test_get_client_ip_x_forwarded_for_multiple(request_factory: RequestFactory) -> None:
    request = request_factory.get("/", HTTP_X_FORWARDED_FOR="192.168.1.1,172.18.0.1")
    assert get_client_ip(request) == "192.168.1.1"


def test_get_client_ip_remote_addr(request_factory: RequestFactory) -> None:
    request = request_factory.get("/", REMOTE_ADDR="localhost")
    assert get_client_ip(request) == "localhost"
