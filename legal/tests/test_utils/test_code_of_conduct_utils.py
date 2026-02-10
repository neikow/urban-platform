from unittest.mock import patch, MagicMock
from django.utils import timezone


class TestHasValidCodeOfConductConsent:
    @patch("legal.utils.CodeOfConductConsent")
    def test_returns_false_when_no_consent_exists(self, mock_consent_model):
        mock_user = MagicMock()
        mock_consent_model.objects.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        from legal.utils import has_valid_code_of_conduct_consent

        result = has_valid_code_of_conduct_consent(mock_user)

        assert result is False
        mock_consent_model.objects.filter.assert_called_once_with(user=mock_user)

    @patch("legal.utils.CodeOfConductConsent")
    def test_returns_false_when_consent_not_up_to_date(self, mock_consent_model):
        mock_user = MagicMock()
        mock_consent = MagicMock()
        mock_consent.is_up_to_date.return_value = False
        mock_consent_model.objects.filter.return_value.order_by.return_value.first.return_value = (
            mock_consent
        )

        from legal.utils import has_valid_code_of_conduct_consent

        result = has_valid_code_of_conduct_consent(mock_user)

        assert result is False
        mock_consent.is_up_to_date.assert_called_once()

    @patch("legal.utils.CodeOfConductConsent")
    def test_returns_true_when_consent_is_valid(self, mock_consent_model):
        mock_user = MagicMock()
        mock_consent = MagicMock()
        mock_consent.is_up_to_date.return_value = True
        mock_consent_model.objects.filter.return_value.order_by.return_value.first.return_value = (
            mock_consent
        )

        from legal.utils import has_valid_code_of_conduct_consent

        result = has_valid_code_of_conduct_consent(mock_user)

        assert result is True


class TestGetLatestCodeOfConductRevision:
    @patch("legal.utils.CodeOfConductPage")
    def test_returns_latest_revision(self, mock_page_model):
        mock_page = MagicMock()
        mock_revision = MagicMock()
        mock_page.revisions.order_by.return_value.first.return_value = mock_revision
        mock_page_model.objects.live.return_value.first.return_value = mock_page
        from legal.utils import get_latest_code_of_conduct_revision

        result = get_latest_code_of_conduct_revision()

        assert result is mock_revision
        mock_page.revisions.order_by.assert_called_once_with("-created_at")


class TestCreateCodeOfConductConsentRecord:
    @patch("legal.utils.timezone")
    @patch("legal.utils.get_latest_code_of_conduct_revision")
    @patch("legal.utils.CodeOfConductConsent")
    def test_creates_consent_record(self, mock_consent_model, mock_get_revision, mock_timezone):
        mock_user = MagicMock()
        mock_revision = MagicMock()
        mock_now = timezone.now()
        mock_consent_record = MagicMock()

        mock_get_revision.return_value = mock_revision
        mock_timezone.now.return_value = mock_now
        mock_consent_model.objects.create.return_value = mock_consent_record

        from legal.utils import create_code_of_conduct_consent_record

        result = create_code_of_conduct_consent_record(mock_user, consent_ip="192.168.1.1")

        assert result == mock_consent_record
        mock_consent_model.objects.create.assert_called_once_with(
            user=mock_user,
            policy_revision=mock_revision,
            consent_ip="192.168.1.1",
            consented_at=mock_now,
        )

    @patch("legal.utils.timezone")
    @patch("legal.utils.get_latest_code_of_conduct_revision")
    @patch("legal.utils.CodeOfConductConsent")
    def test_creates_consent_record_without_ip(
        self, mock_consent_model, mock_get_revision, mock_timezone
    ):
        mock_user = MagicMock()
        mock_revision = MagicMock()
        mock_now = timezone.now()

        mock_get_revision.return_value = mock_revision
        mock_timezone.now.return_value = mock_now

        from legal.utils import create_code_of_conduct_consent_record

        create_code_of_conduct_consent_record(mock_user)

        mock_consent_model.objects.create.assert_called_once_with(
            user=mock_user, policy_revision=mock_revision, consent_ip=None, consented_at=mock_now
        )
