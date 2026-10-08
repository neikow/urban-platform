from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives, send_mail
from django.urls import reverse

from core.emails.backend import EmailServiceBackend
from core.models import User, UserRole
from home.models import HomePage
from legal.models import CodeOfConductPage, PrivacyPolicyPage
from publications.models import ProjectPage, PublicationIndexPage


def make_user(role: str, email: str, **fields: object) -> User:
    return User.objects.create_user(
        email=email, password="pass12345", first_name="First", last_name="Last", role=role, **fields
    )


@pytest.fixture
def index(db):
    index = PublicationIndexPage.objects.first()
    if index is None:
        index = PublicationIndexPage(title="Actualités", slug="actualites")
        HomePage.objects.get(slug="home").add_child(instance=index)
        index.save_revision().publish()
    return index


@pytest.mark.django_db
class TestModerationWorkflow:
    def submit(self, index, editor):
        page = ProjectPage(title="Nouveau square", slug="square", live=False, description="d")
        index.add_child(instance=page)
        page.save_revision(user=editor)
        page.get_workflow().start(page, editor)
        return page

    def test_moderators_are_emailed_when_an_editor_submits(self, index):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")
        admin = make_user(UserRole.ADMIN, "admin@example.com")
        away = make_user(UserRole.MODERATOR, "away@example.com")
        away.is_active = False
        away.save()

        self.submit(index, editor)

        recipients = {address for message in mail.outbox for address in message.to}
        assert {moderator.email, admin.email} <= recipients
        assert away.email not in recipients
        assert editor.email not in recipients
        assert any("Nouveau square" in message.subject for message in mail.outbox)

    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_the_editor_hears_back(self, index, action):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")
        page = self.submit(index, editor)
        mail.outbox.clear()

        task_state = page.current_workflow_task_state
        task_state.task.specific.on_action(task_state, moderator, action)

        assert editor.email in {address for message in mail.outbox for address in message.to}
        page.refresh_from_db()
        assert page.live is (action == "approve")

    def test_editors_cannot_publish(self, index):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        page = ProjectPage(title="Brouillon", slug="brouillon", live=False, description="d")
        index.add_child(instance=page)

        permissions = page.permissions_for_user(editor)

        assert permissions.can_edit()
        assert not permissions.can_publish()

    def test_moderators_can_publish(self, index):
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")
        page = ProjectPage(title="Brouillon", slug="brouillon", live=False, description="d")
        index.add_child(instance=page)

        assert page.permissions_for_user(moderator).can_publish()


@pytest.mark.django_db
class TestLegalPages:
    @pytest.mark.parametrize("role", [UserRole.EDITOR, UserRole.MODERATOR])
    def test_read_only_below_administrators(self, client, role):
        user = make_user(role, f"{role}@example.com")
        policy = PrivacyPolicyPage.objects.first()
        code = CodeOfConductPage.objects.first()

        for page in (policy, code):
            permissions = page.permissions_for_user(user)
            assert not permissions.can_edit()
            assert not permissions.can_publish()
            assert not permissions.can_delete()

        client.force_login(user)
        response = client.get(reverse("wagtailadmin_pages:edit", args=[policy.pk]))
        assert response.status_code in (302, 403)

    def test_administrators_edit_them(self, client):
        admin = make_user(UserRole.ADMIN, "admin@example.com")
        policy = PrivacyPolicyPage.objects.first()

        assert policy.permissions_for_user(admin).can_edit()
        assert policy.permissions_for_user(admin).can_publish()
        client.force_login(admin)
        assert client.get(reverse("wagtailadmin_pages:edit", args=[policy.pk])).status_code == 200

    def test_other_pages_stay_editable(self):
        editor = make_user(UserRole.EDITOR, "editor@example.com")

        assert HomePage.objects.get(slug="home").permissions_for_user(editor).can_edit()


@pytest.mark.django_db
class TestParticipationStatistics:
    @pytest.mark.parametrize("name", ["vote_statistics", "idea_statistics"])
    def test_moderators_and_administrators_only(self, client, name):
        editor = make_user(UserRole.EDITOR, "editor@example.com")
        moderator = make_user(UserRole.MODERATOR, "moderator@example.com")

        client.force_login(editor)
        assert client.get(reverse(name)).status_code in (302, 403)
        client.force_login(moderator)
        assert client.get(reverse(name)).status_code == 200


class TestEmailServiceBackend:
    @pytest.fixture
    def service(self):
        service = MagicMock()
        service.send_email.return_value = True
        with patch("core.emails.backend.get_email_service", return_value=service):
            yield service

    def test_sends_html_alternative_to_each_recipient(self, service):
        message = EmailMultiAlternatives(
            "Sujet", "texte", to=["a@example.com"], cc=["b@example.com"]
        )
        message.attach_alternative("<p>html</p>", "text/html")

        assert EmailServiceBackend().send_messages([message]) == 2
        sent = [call.kwargs for call in service.send_email.call_args_list]
        assert [c["to_email"] for c in sent] == ["a@example.com", "b@example.com"]
        assert all(c["html_content"] == "<p>html</p>" and c["subject"] == "Sujet" for c in sent)

    def test_plain_text_is_escaped(self, service, settings):
        settings.EMAIL_BACKEND = "core.emails.backend.EmailServiceBackend"

        send_mail("Sujet", "Ligne <1>\nLigne 2", None, ["a@example.com"])

        html = service.send_email.call_args.kwargs["html_content"]
        assert "&lt;1&gt;" in html and "<br>" in html

    def test_failures_raise_unless_silent(self, service):
        service.send_email.side_effect = RuntimeError("down")
        message = EmailMultiAlternatives("Sujet", "texte", to=["a@example.com"])

        with pytest.raises(RuntimeError):
            EmailServiceBackend().send_messages([message])
        assert EmailServiceBackend(fail_silently=True).send_messages([message]) == 0
