"""Renewal reminders, the memberships dashboard, and what a CIQ's responsible sees."""

from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse

from core.membership_reminders import due_reminders, send_membership_reminders
from core.models import (
    EmailEvent,
    Membership,
    MembershipReminder,
    NeighborhoodAssociation,
    User,
    UserRole,
)

END = date(2026, 12, 31)


def make_user(email: str, role: str = UserRole.CITIZEN, **kwargs) -> User:
    return User.objects.create_user(
        email=email,
        password="Password123",
        first_name="First",
        last_name="Last",
        role=role,
        **kwargs,
    )


@pytest.fixture
def resident(db):
    return make_user("resident@example.com")


@pytest.fixture
def membership(resident):
    return Membership.objects.create(user=resident, starts_on=date(2026, 3, 1), ends_on=END)


def kinds(today: date) -> list[str]:
    return [kind for _membership, kind in due_reminders(today)]


@pytest.mark.django_db
class TestDueReminders:
    @pytest.mark.parametrize(
        "today, expected",
        [
            (date(2026, 12, 14), []),
            (date(2026, 12, 15), ["expiring"]),
            (date(2026, 12, 30), ["expiring"]),
            (date(2026, 12, 31), []),
            (date(2027, 1, 1), ["grace"]),
            (date(2027, 1, 7), ["grace"]),
            (date(2027, 1, 8), []),
            (date(2027, 1, 25), ["last_call"]),
            (date(2027, 1, 31), ["last_call"]),
            (date(2027, 2, 1), []),
        ],
    )
    def test_windows(self, membership, today, expected):
        assert kinds(today) == expected

    def test_renewed_members_are_not_reminded(self, resident, membership):
        Membership.objects.create(
            user=resident, starts_on=date(2027, 1, 1), ends_on=date(2027, 12, 31)
        )

        assert kinds(date(2026, 12, 15)) == []
        assert kinds(date(2027, 1, 2)) == []

    def test_open_ended_renewal(self, resident, membership):
        Membership.objects.create(user=resident, starts_on=date(2026, 6, 1), ends_on=None)

        assert kinds(date(2026, 12, 15)) == []

    def test_inactive_accounts_are_not_reminded(self, resident, membership):
        resident.is_active = False
        resident.save()

        assert kinds(date(2026, 12, 15)) == []


@pytest.mark.django_db
class TestSendReminders:
    def test_each_reminder_is_sent_once(self, membership, django_capture_on_commit_callbacks):
        with (
            patch("core.emails.tasks.send_membership_email.delay") as delay,
            django_capture_on_commit_callbacks(execute=True),
        ):
            assert send_membership_reminders(date(2026, 12, 15)) == 1
            assert send_membership_reminders(date(2026, 12, 16)) == 0
            assert send_membership_reminders(date(2027, 1, 1)) == 1

        assert MembershipReminder.objects.filter(membership=membership).count() == 2
        assert [call.args[1] for call in delay.call_args_list] == ["expiring", "grace"]
        assert delay.call_args_list[0].args[0] == membership.user_id
        assert "grace_until" in delay.call_args_list[0].args[2]

    @pytest.mark.parametrize("kind", ["confirmation", "expiring", "grace", "last_call"])
    def test_emails_render(self, resident, kind):
        from core.emails.tasks import send_membership_email

        with patch(
            "core.emails.services.ConsoleEmailService.send_email", return_value=True
        ) as send:
            assert send_membership_email(
                resident.pk,
                kind,
                {
                    "ends_on": "31 décembre 2026",
                    "grace_until": "31 janvier 2027",
                    "association": "Frioul",
                },
            )

        html = send.call_args.kwargs["html_content"]
        assert reverse("membership") in html
        assert "31 d" in html
        assert EmailEvent.objects.get().recipient_email == resident.email


# --- admin ----------------------------------------------------------------------


@pytest.fixture
def two_ciqs(db):
    responsible = make_user("president@example.com", UserRole.EDITOR)
    frioul = NeighborhoodAssociation.objects.create(name="Frioul", responsible=responsible)
    bompard = NeighborhoodAssociation.objects.create(name="Bompard")
    today = date.today()
    for index, association in enumerate([frioul, frioul, bompard]):
        user = make_user(f"member{index}@example.com")
        Membership.objects.create(
            user=user, association=association, starts_on=today, ends_on=date(today.year, 12, 31)
        )
    return responsible, frioul, bompard


@pytest.mark.django_db
class TestResponsibleOfACiq:
    def test_sees_the_members_of_their_ciq_only(self, client, two_ciqs):
        responsible, frioul, _bompard = two_ciqs
        client.force_login(responsible)

        response = client.get(reverse("membership:index"))

        assert response.status_code == 200
        shown = {m.association for m in response.context["object_list"]}
        assert shown == {frioul}

    def test_cannot_record_memberships(self, client, two_ciqs):
        client.force_login(two_ciqs[0])

        assert client.get(reverse("membership:add")).status_code in (302, 403)

    def test_other_editors_see_nothing(self, client, two_ciqs):
        client.force_login(make_user("editor@example.com", UserRole.EDITOR))

        assert client.get(reverse("membership:index")).status_code in (302, 403)

    def test_administrators_see_everyone(self, client, two_ciqs):
        client.force_login(make_user("admin@example.com", UserRole.ADMIN))

        response = client.get(reverse("membership:index"))

        assert len(response.context["object_list"]) == 3

    def test_year_filter(self, client, two_ciqs, resident):
        Membership.objects.create(
            user=resident, starts_on=date(2020, 1, 1), ends_on=date(2020, 12, 31)
        )
        client.force_login(make_user("admin@example.com", UserRole.ADMIN))

        response = client.get(reverse("membership:index"), {"year": "2020"})

        assert [m.user for m in response.context["object_list"]] == [resident]


@pytest.mark.django_db
class TestMembershipsPanel:
    def panel(self, client, user):
        client.force_login(user)
        response = client.get(reverse("wagtailadmin_home"))
        return response, response.content.decode()

    def test_responsible_sees_their_ciq(self, client, two_ciqs):
        responsible, frioul, bompard = two_ciqs

        _response, content = self.panel(client, responsible)

        assert 'id="memberships' in content or "memberships-heading" in content
        assert f"?association={frioul.pk}" in content
        assert f"?association={bompard.pk}" not in content

    def test_administrators_see_every_ciq(self, client, two_ciqs):
        _responsible, frioul, bompard = two_ciqs

        _response, content = self.panel(client, make_user("admin@example.com", UserRole.ADMIN))

        assert f"?association={frioul.pk}" in content
        assert f"?association={bompard.pk}" in content

    def test_not_for_other_editors(self, client, two_ciqs):
        _response, content = self.panel(client, make_user("editor@example.com", UserRole.EDITOR))

        assert "?association=" not in content
