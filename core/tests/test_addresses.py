import io
import json
from typing import Any
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse

from core import geocoding
from core.associations import association_at, reassign_residents, set_address
from core.geocoding import Address, GeocodingUnavailable, geocode, locate, search_addresses
from core.models import NeighborhoodAssociation, User, UserRole
from core.tasks import reassign_residents as reassign_residents_task

# Captured before the autouse offline_geocoding fixture replaces it.
real_fetch = geocoding._fetch

PARADIS = Address(
    label="12 Rue Paradis 13001 Marseille", postcode="13001", lon=5.3764, lat=43.2942, score=0.97
)
PRADO = Address(
    label="1 Avenue du Prado 13006 Marseille", postcode="13006", lon=5.3810, lat=43.2830, score=0.95
)

# Two squares side by side, around each address.
AREA_PARADIS = {
    "type": "Polygon",
    "coordinates": [[[5.37, 43.29], [5.38, 43.29], [5.38, 43.30], [5.37, 43.30], [5.37, 43.29]]],
}
AREA_PRADO = {
    "type": "Polygon",
    "coordinates": [[[5.37, 43.28], [5.39, 43.28], [5.39, 43.29], [5.37, 43.29], [5.37, 43.28]]],
}


def answers(*addresses: Address):
    """Stand-in for geocoding._fetch: the given addresses, whatever the query."""

    def fetch(query: str, limit: int, autocomplete: bool) -> list[Address]:
        return list(addresses[:limit])

    return fetch


def api_response(features: list[dict[str, Any]]) -> io.BytesIO:
    return io.BytesIO(json.dumps({"type": "FeatureCollection", "features": features}).encode())


FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [5.3764, 43.2942]},
    "properties": {"label": PARADIS.label, "postcode": "13001", "score": 0.97, "citycode": "13201"},
}


# --- geocoding ----------------------------------------------------------------


class TestFetch:
    def test_queries_marseille_and_parses_features(self, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", real_fetch)
        with patch("core.geocoding.urlopen", return_value=api_response([FEATURE])) as urlopen:
            results = search_addresses("12 rue paradis")

        assert results == [PARADIS]
        params = parse_qs(urlparse(urlopen.call_args.args[0].full_url).query)
        assert params["citycode"] == [geocoding.CITY_CODE]
        assert params["autocomplete"] == ["1"]
        assert params["q"] == ["12 rue paradis"]

    @pytest.mark.parametrize("error", [URLError("down"), TimeoutError(), ValueError("not json")])
    def test_failures_raise_unavailable(self, monkeypatch, error):
        monkeypatch.setattr(geocoding, "_fetch", real_fetch)
        with (
            patch("core.geocoding.urlopen", side_effect=error),
            pytest.raises(GeocodingUnavailable),
        ):
            search_addresses("12 rue paradis")


class TestSearchAndGeocode:
    def test_short_queries_are_not_sent(self, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))
        assert search_addresses("  12 ") == []

    def test_geocode_returns_best_match(self, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS, PRADO))
        assert geocode("12 rue paradis") == PARADIS

    def test_geocode_rejects_weak_matches(self, monkeypatch):
        weak = Address(label="Marseille", postcode="", lon=5.4, lat=43.3, score=0.2)
        monkeypatch.setattr(geocoding, "_fetch", answers(weak))
        assert geocode("somewhere in Lyon") is None

    def test_locate_keeps_current_point_when_service_is_down(self):
        current = PRADO.point
        assert locate("1 avenue du prado", current) == current

    def test_locate_clears_point_of_empty_address(self, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))
        assert locate("", PRADO.point) is None
        assert locate("12 rue paradis", None) == PARADIS.point


class TestAddressSearchView:
    def test_returns_suggestions(self, client, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS, PRADO))

        response = client.get(reverse("address_search"), {"q": "rue"})

        assert response.status_code == 200
        assert [r["label"] for r in response.json()["results"]] == [PARADIS.label, PRADO.label]
        assert response.json()["results"][0]["lon"] == PARADIS.lon

    def test_service_down(self, client):
        response = client.get(reverse("address_search"), {"q": "12 rue paradis"})

        assert response.status_code == 503
        assert response.json()["results"] == []


# --- associations -------------------------------------------------------------


def reassignments(callbacks) -> int:
    """Queued reassignment tasks (Wagtail queues its own tasks on commit too)."""
    task = reassign_residents_task.delay  # type: ignore[attr-defined]  # Celery task
    return sum(callback == task for callback in callbacks)


@pytest.fixture
def paradis_association(db):
    return NeighborhoodAssociation.objects.create(name="Paradis", area=AREA_PARADIS)


@pytest.fixture
def prado_association(db):
    return NeighborhoodAssociation.objects.create(name="Prado", area=AREA_PRADO)


@pytest.fixture
def resident(db):
    return User.objects.create_user(
        email="resident@example.com", password="Password123", first_name="Res", last_name="Ident"
    )


@pytest.mark.django_db
class TestAssociationAssignment:
    def test_association_at_point(self, paradis_association, prado_association):
        assert association_at(PARADIS.point) == paradis_association
        assert association_at(PRADO.point) == prado_association
        assert association_at({"type": "Point", "coordinates": [5.5, 43.4]}) is None
        assert association_at(None) is None

    def test_set_address_attaches_association(self, paradis_association, resident):
        set_address(resident, PARADIS.label, PARADIS.point)

        assert resident.address == PARADIS.label
        assert resident.location == PARADIS.point
        assert resident.association == paradis_association

    def test_residents_follow_a_redrawn_area(
        self, paradis_association, prado_association, resident, django_capture_on_commit_callbacks
    ):
        set_address(resident, PARADIS.label, PARADIS.point)
        resident.save()

        # The Prado area grows over the Paradis address; Paradis is now drawn elsewhere.
        prado_association.area = {
            "type": "Polygon",
            "coordinates": [
                [[5.36, 43.28], [5.39, 43.28], [5.39, 43.30], [5.36, 43.30], [5.36, 43.28]]
            ],
        }
        paradis_association.area = None
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            paradis_association.save()
            prado_association.save()

        assert reassignments(callbacks) == 2

        resident.refresh_from_db()
        assert resident.association == prado_association

    def test_residents_leave_a_deleted_association(
        self, paradis_association, resident, django_capture_on_commit_callbacks
    ):
        set_address(resident, PARADIS.label, PARADIS.point)
        resident.save()

        with django_capture_on_commit_callbacks(execute=True):
            paradis_association.delete()

        resident.refresh_from_db()
        assert resident.association is None
        assert resident.location == PARADIS.point

    def test_only_a_changed_area_queues_a_reassignment(
        self, paradis_association, django_capture_on_commit_callbacks
    ):
        association = NeighborhoodAssociation.objects.get(pk=paradis_association.pk)
        with django_capture_on_commit_callbacks() as callbacks:
            association.website = "https://paradis.example"
            association.save()
        assert reassignments(callbacks) == 0

        with django_capture_on_commit_callbacks() as callbacks:
            association.area = AREA_PRADO
            association.save()
            association.save()
        assert reassignments(callbacks) == 1

    def test_creating_an_area_queues_a_reassignment(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks() as callbacks:
            NeighborhoodAssociation.objects.create(name="Sans secteur")
            NeighborhoodAssociation.objects.create(name="Paradis", area=AREA_PARADIS)
        assert reassignments(callbacks) == 1

    def test_reassign_counts_changes(self, paradis_association, resident):
        User.objects.filter(pk=resident.pk).update(location=PARADIS.point)
        assert reassign_residents() == 1
        assert reassign_residents() == 0

    def test_clean_locates_the_address(self, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers(PRADO))
        association = NeighborhoodAssociation(name="Prado", address="1 avenue du prado")

        association.full_clean()

        assert association.address_location == PRADO.point

    def test_area_must_be_a_polygon(self):
        association = NeighborhoodAssociation(name="Prado", area=PRADO.point)
        with pytest.raises(Exception) as error:
            association.full_clean()
        assert "area" in error.value.message_dict  # type: ignore[attr-defined]


@pytest.mark.django_db
class TestAssociationAdmin:
    @pytest.fixture
    def admin_client(self, client):
        user = User.objects.create_superuser(email="super@example.com", password="pass12345")
        client.force_login(user)
        return client

    def test_edit_form_shows_other_areas_only(
        self, admin_client, paradis_association, prado_association
    ):
        url = reverse("neighborhood_association:edit", args=[paradis_association.pk])

        content = admin_client.get(url).content.decode()

        assert "<geojson-map-input" in content
        assert "data-reference=" in content
        assert "&quot;name&quot;: &quot;Prado&quot;" in content
        assert "&quot;name&quot;: &quot;Paradis&quot;" not in content
        assert "<address-input" in content

    def test_create_with_area(self, admin_client, resident, django_capture_on_commit_callbacks):
        set_address(resident, PARADIS.label, PARADIS.point)
        resident.save()
        responsible = User.objects.create_user(
            email="member@example.com", password="pass12345", role=UserRole.ASSOCIATION_MEMBER
        )

        with django_capture_on_commit_callbacks(execute=True):
            response = admin_client.post(
                reverse("neighborhood_association:add"),
                {
                    "name": "Paradis",
                    "responsible": responsible.pk,
                    "address": "",
                    "area": json.dumps(AREA_PARADIS),
                    "contact_email": "contact@paradis.example",
                    "contact_phone": "04 91 00 00 00",
                    "website": "https://paradis.example",
                },
            )

        assert response.status_code == 302
        association = NeighborhoodAssociation.objects.get(name="Paradis")
        assert association.area == AREA_PARADIS
        assert association.responsible == responsible
        resident.refresh_from_db()
        assert resident.association == association


# --- users --------------------------------------------------------------------

REGISTRATION = {
    "email": "new@example.com",
    "password": "SecurePass123",
    "confirm_password": "SecurePass123",
    "first_name": "New",
    "last_name": "User",
    "postal_code": "13001",
    "accept_terms": True,
}


@pytest.mark.django_db
class TestRegistrationAddress:
    @pytest.fixture(autouse=True)
    def no_emails(self):
        with patch("core.views.register.send_verification_email"):
            yield

    def test_address_attaches_the_new_user(self, client, monkeypatch, paradis_association):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))

        response = client.post(reverse("register"), {**REGISTRATION, "address": "12 rue paradis"})

        assert response.status_code == 302
        user = User.objects.get(email="new@example.com")
        assert user.address == PARADIS.label
        assert user.location == PARADIS.point
        assert user.association == paradis_association

    def test_address_is_optional(self, client):
        response = client.post(reverse("register"), REGISTRATION)

        assert response.status_code == 302
        user = User.objects.get(email="new@example.com")
        assert user.address == ""
        assert user.association is None

    def test_unknown_address_is_refused(self, client, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers())

        response = client.post(reverse("register"), {**REGISTRATION, "address": "nowhere at all"})

        assert response.status_code == 200
        assert "address" in response.context["form"].errors
        assert not User.objects.filter(email="new@example.com").exists()

    def test_address_kept_unlocated_when_service_is_down(self, client):
        response = client.post(reverse("register"), {**REGISTRATION, "address": "12 rue paradis"})

        assert response.status_code == 302
        user = User.objects.get(email="new@example.com")
        assert user.address == "12 rue paradis"
        assert user.location is None

    def test_form_renders_autocomplete(self, client):
        content = client.get(reverse("register")).content.decode()

        assert "<address-input" in content
        assert 'data-postcode-field="postal_code"' in content
        assert "dist/address-input.js" in content


@pytest.mark.django_db
class TestProfileAddress:
    PROFILE = {
        "email": "resident@example.com",
        "first_name": "Res",
        "last_name": "Ident",
        "postal_code": "13006",
    }

    def test_changing_address_moves_the_user(
        self, client, monkeypatch, resident, paradis_association, prado_association
    ):
        set_address(resident, PARADIS.label, PARADIS.point)
        resident.save()
        client.force_login(resident)
        monkeypatch.setattr(geocoding, "_fetch", answers(PRADO))

        client.post(reverse("profile_edit"), {**self.PROFILE, "address": "1 avenue du prado"})

        resident.refresh_from_db()
        assert resident.address == PRADO.label
        assert resident.association == prado_association

    def test_unchanged_address_keeps_location_when_service_is_down(
        self, client, resident, paradis_association
    ):
        set_address(resident, PARADIS.label, PARADIS.point)
        resident.save()
        client.force_login(resident)

        client.post(reverse("profile_edit"), {**self.PROFILE, "address": PARADIS.label})

        resident.refresh_from_db()
        assert resident.location == PARADIS.point
        assert resident.association == paradis_association

    def test_soft_delete_forgets_the_address(self, resident, paradis_association):
        set_address(resident, PARADIS.label, PARADIS.point)
        resident.save()

        resident.soft_delete()

        assert (resident.address, resident.location, resident.association) == ("", None, None)
