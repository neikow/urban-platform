import pytest
from django.urls import reverse

from core.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="consent@example.com", password="TestPass123!", first_name="C", last_name="D"
    )


class TestSetNewsletterSubscription:
    def test_subscribing_records_the_date(self, user):
        user.set_newsletter_subscription(True)

        assert user.newsletter_subscription is True
        assert user.newsletter_consent_at is not None

    def test_staying_subscribed_keeps_the_original_date(self, user):
        user.set_newsletter_subscription(True)
        first = user.newsletter_consent_at

        user.set_newsletter_subscription(True)

        assert user.newsletter_consent_at == first

    def test_unsubscribing_clears_the_date(self, user):
        user.set_newsletter_subscription(True)
        user.set_newsletter_subscription(False)

        assert user.newsletter_consent_at is None


@pytest.mark.django_db
def test_profile_edit_records_consent(client, user):
    client.force_login(user)

    client.post(
        reverse("profile_edit"),
        {
            "email": user.email,
            "first_name": "C",
            "last_name": "D",
            "postal_code": "13007",
            "newsletter_subscription": "on",
        },
    )

    user.refresh_from_db()
    assert user.newsletter_subscription is True
    assert user.newsletter_consent_at is not None


@pytest.mark.django_db
def test_soft_delete_clears_consent(user):
    user.set_newsletter_subscription(True)
    user.save()

    user.soft_delete()

    assert user.newsletter_consent_at is None
