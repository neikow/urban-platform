import pytest


@pytest.fixture
def test_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="testuser@example.com",
        password="TestPass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def another_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="another@example.com",
        password="AnotherPass123",
        first_name="Another",
        last_name="User",
    )
