import pytest

from core import geocoding
from core.geocoding import Address
from publications.tests.test_event_interest import index, make_event  # noqa: F401  (fixture)

PLACE = Address(
    label="1 Rue d'Endoume 13007 Marseille", postcode="13007", lon=5.36, lat=43.29, score=0.9
)


@pytest.mark.django_db
class TestEventAddress:
    def test_saving_locates_the_address(self, index, monkeypatch):  # noqa: F811
        monkeypatch.setattr(geocoding, "_fetch", lambda *args, **kwargs: [PLACE])

        event = make_event(index)

        event.refresh_from_db()
        assert event.address_location == PLACE.point

    def test_no_address_no_location(self, index, monkeypatch):  # noqa: F811
        monkeypatch.setattr(geocoding, "_fetch", lambda *args, **kwargs: [PLACE])

        event = make_event(index)
        event.address = ""
        event.save_revision().publish()

        event.refresh_from_db()
        assert event.address_location is None

    def test_address_field_suggests_addresses(self):
        from publications.models import EventPage

        form_class = EventPage.get_edit_handler().get_form_class()

        assert "<address-input" in form_class().fields["address"].widget.render("address", "")
