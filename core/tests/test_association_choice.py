"""Choosing a neighborhood association (CIQ), the nearest one by default, and importing them."""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse

from core import geocoding
from core.associations import (
    attach_association,
    distance_meters,
    nearest_association,
    paused_reassignment,
    queue_reassignment,
    ranked_associations,
    reassign_residents,
    set_address,
)
from core.management.commands.import_associations import federation_of
from core.models import NeighborhoodAssociation, User
from core.views.auth_mixins import AssociationChoiceField, format_distance
from core.tests.test_addresses import AREA_PARADIS, PARADIS, PRADO, answers, reassignments


def point(lon: float, lat: float) -> dict:
    return {"type": "Point", "coordinates": [lon, lat]}


# Seats along the Corniche, from north to south.
CATALANS = point(5.3606, 43.2905)
AUFFES = point(5.3492, 43.2853)
ENDOUME = point(5.3546, 43.2820)
HOME_NEAR_AUFFES = point(5.3500, 43.2850)


@pytest.fixture
def catalans(db):
    return NeighborhoodAssociation.objects.create(
        name="Pharo Catalans", code="701", address_location=CATALANS
    )


@pytest.fixture
def auffes(db):
    return NeighborhoodAssociation.objects.create(
        name="Vallon des Auffes", code="702", address_location=AUFFES
    )


@pytest.fixture
def unlocated(db):
    return NeighborhoodAssociation.objects.create(name="Place 4 Septembre", code="704")


@pytest.fixture
def resident(db):
    return User.objects.create_user(
        email="resident@example.com", password="Password123", first_name="Res", last_name="Ident"
    )


class TestDistances:
    def test_distance_between_two_points(self):
        # About 1.3 km between rue Paradis and the Prado.
        assert 1200 < distance_meters(PARADIS.point, PRADO.point) < 1400
        assert distance_meters(CATALANS, CATALANS) == 0

    def test_format_distance(self):
        assert format_distance(3) == "10 m"
        assert format_distance(346) == "350 m"
        assert format_distance(1234).replace(",", ".") == "1.2 km"


@pytest.mark.django_db
class TestNearestAssociation:
    def test_nearest_seat(self, catalans, auffes, unlocated):
        assert nearest_association(HOME_NEAR_AUFFES) == auffes
        assert nearest_association(CATALANS) == catalans
        assert nearest_association(None) is None

    def test_an_area_wins_over_a_nearer_seat(self, catalans):
        paradis = NeighborhoodAssociation.objects.create(name="Paradis", area=AREA_PARADIS)
        catalans.address_location = PARADIS.point
        catalans.save()

        assert nearest_association(PARADIS.point) == paradis

    def test_no_located_association(self, unlocated):
        assert nearest_association(HOME_NEAR_AUFFES) is None

    def test_ranking_puts_unlocated_last(self, catalans, auffes, unlocated):
        ranked = ranked_associations(HOME_NEAR_AUFFES)

        assert [a for a, _ in ranked] == [auffes, catalans, unlocated]
        assert ranked[0][1] < ranked[1][1]
        assert ranked[2][1] is None

    def test_ranking_without_a_point_keeps_names_order(self, catalans, auffes, unlocated):
        assert ranked_associations(None) == [(catalans, None), (unlocated, None), (auffes, None)]


@pytest.mark.django_db
class TestAttachAssociation:
    def test_follows_the_address_by_default(self, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES)

        assert resident.association == auffes
        assert not resident.association_chosen

    def test_choosing_another_association(self, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, catalans)

        assert resident.association == catalans
        assert resident.association_chosen

    def test_choosing_the_nearest_is_not_a_choice(self, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, auffes)

        assert resident.association == auffes
        assert not resident.association_chosen

    def test_choice_without_an_address(self, resident, catalans):
        attach_association(resident, catalans)

        assert resident.association == catalans
        assert resident.association_chosen

    def test_reassignment_keeps_choices(self, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, catalans)
        resident.save()
        other = User.objects.create_user(email="other@example.com", password="Password123")
        User.objects.filter(pk=other.pk).update(location=HOME_NEAR_AUFFES)

        assert reassign_residents() == 1

        resident.refresh_from_db()
        other.refresh_from_db()
        assert resident.association == catalans
        assert other.association == auffes

    def test_deleting_the_chosen_association(
        self, resident, catalans, auffes, django_capture_on_commit_callbacks
    ):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, catalans)
        resident.save()

        with django_capture_on_commit_callbacks(execute=True):
            catalans.delete()

        resident.refresh_from_db()
        assert resident.association == auffes
        assert not resident.association_chosen

    def test_a_moved_seat_queues_a_reassignment(self, catalans, django_capture_on_commit_callbacks):
        association = NeighborhoodAssociation.objects.get(pk=catalans.pk)
        with django_capture_on_commit_callbacks() as callbacks:
            association.website = "https://catalans.example"
            association.save()
        assert reassignments(callbacks) == 0

        with django_capture_on_commit_callbacks() as callbacks:
            association.address_location = AUFFES
            association.save()
        assert reassignments(callbacks) == 1

    def test_paused_reassignment_queues_once(self, db, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks() as callbacks:
            with paused_reassignment():
                queue_reassignment()
                queue_reassignment()
        assert reassignments(callbacks) == 1

        with django_capture_on_commit_callbacks() as callbacks:
            with paused_reassignment():
                pass
        assert reassignments(callbacks) == 0


@pytest.mark.django_db
class TestNearestAssociationsView:
    def test_lists_nearest_first(self, client, catalans, auffes, unlocated):
        response = client.get(reverse("nearest_associations"), {"lon": 5.35, "lat": 43.285})

        assert response.status_code == 200
        results = response.json()["results"]
        assert [r["id"] for r in results] == [auffes.pk, catalans.pk, unlocated.pk]
        assert isinstance(results[0]["distance"], int)
        assert results[2]["distance"] is None

    @pytest.mark.parametrize("query", [{}, {"lon": "x", "lat": "43"}, {"lon": "5", "lat": "91"}])
    def test_invalid_point(self, client, query):
        response = client.get(reverse("nearest_associations"), query)

        assert response.status_code == 400


@pytest.mark.django_db
class TestAssociationFields:
    REGISTRATION = {
        "email": "new@example.com",
        "password": "SecurePass123",
        "confirm_password": "SecurePass123",
        "first_name": "New",
        "last_name": "User",
        "postal_code": "13007",
        "accept_terms": True,
    }
    PROFILE = {
        "email": "resident@example.com",
        "first_name": "Res",
        "last_name": "Ident",
        "postal_code": "13007",
    }

    @pytest.fixture(autouse=True)
    def no_emails(self):
        with patch("core.views.register.send_verification_email"):
            yield

    def test_field_labels_show_distances(self, catalans, auffes, unlocated):
        field = AssociationChoiceField()
        field.rank_from(HOME_NEAR_AUFFES)

        labels = [label for _value, label in field.choices][1:]
        assert labels[0].startswith("Vallon des Auffes · ")
        assert labels[0].endswith(" m")
        assert labels[2] == "Place 4 Septembre"

    def test_no_field_without_associations(self, client, db):
        content = client.get(reverse("register")).content.decode()

        assert "<association-select" not in content

    def test_register_renders_the_picker(self, client, catalans):
        content = client.get(reverse("register")).content.decode()

        assert "<association-select" in content
        assert reverse("nearest_associations") in content
        assert "dist/association-select.js" in content

    def test_register_with_a_choice(self, client, monkeypatch, catalans, auffes):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))
        NeighborhoodAssociation.objects.filter(pk=auffes.pk).update(address_location=PARADIS.point)

        response = client.post(
            reverse("register"),
            {**self.REGISTRATION, "address": "12 rue paradis", "association": catalans.pk},
        )

        assert response.status_code == 302
        user = User.objects.get(email="new@example.com")
        assert user.association == catalans
        assert user.association_chosen

    def test_register_follows_the_address(self, client, monkeypatch, catalans, auffes):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))
        NeighborhoodAssociation.objects.filter(pk=auffes.pk).update(address_location=PARADIS.point)

        client.post(reverse("register"), {**self.REGISTRATION, "address": "12 rue paradis"})

        user = User.objects.get(email="new@example.com")
        assert user.association == auffes
        assert not user.association_chosen

    def test_profile_changes_only_the_choice(self, client, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES)
        resident.save()
        client.force_login(resident)

        client.post(
            reverse("profile_edit"),
            {**self.PROFILE, "address": "Vallon des Auffes", "association": catalans.pk},
        )
        resident.refresh_from_db()
        assert (resident.association, resident.association_chosen) == (catalans, True)
        assert resident.location == HOME_NEAR_AUFFES

        # Back to "the nearest to my address".
        client.post(reverse("profile_edit"), {**self.PROFILE, "address": "Vallon des Auffes"})
        resident.refresh_from_db()
        assert (resident.association, resident.association_chosen) == (auffes, False)

    def test_profile_shows_the_choice(self, client, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, catalans)
        resident.save()
        client.force_login(resident)

        form = client.get(reverse("profile_edit")).context["form"]

        assert form.initial["association"] == catalans
        # Nearest first.
        assert list(form.fields["association"].queryset)[0] == auffes


# --- import -------------------------------------------------------------------

CSV = """code,name,address,contact_email,contact_phone,website
700,FEDERATION 07,49 rue Charras 13007 Marseille,fede@example.com,,
701,PHARO – CATALANS,49 rue Charras,catalans@example.com,,
702,VALLON DES AUFFES ET CORNICHE,152 rue du Vallon des Auffes,auffes@example.com,,
704,PLACE 4 SEPTEMBRE,,quatre@example.com,,
705,BAD EMAIL,233 Corniche Kennedy,not-an-email>,,
801,ROUET – PRADO – CANTINI,7 rue de Bénédetti 13008 Marseille,rouet@example.com,,
"""


def write_csv(tmp_path: Path, content: str = CSV) -> Path:
    path = tmp_path / "annuaire.csv"
    path.write_text(content, encoding="utf-8")
    return path


def run_import(path: Path, *args: str) -> str:
    out = io.StringIO()
    call_command("import_associations", str(path), *args, stdout=out)
    return out.getvalue()


class TestFederationOf:
    @pytest.mark.parametrize(
        "code, federation",
        [("701", 7), ("716", 7), ("1012", 10), ("700", None), ("1000", None), ("abc", None)],
    )
    def test_codes(self, code, federation):
        assert federation_of(code) == federation


@pytest.mark.django_db
class TestImportAssociations:
    def test_imports_one_federation(
        self, tmp_path, monkeypatch, django_capture_on_commit_callbacks
    ):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))

        with django_capture_on_commit_callbacks() as callbacks:
            output = run_import(write_csv(tmp_path), "--federation", "7")

        codes = set(NeighborhoodAssociation.objects.values_list("code", flat=True))
        assert codes == {"701", "702", "704"}
        catalans = NeighborhoodAssociation.objects.get(code="701")
        assert catalans.name == "PHARO – CATALANS"
        assert catalans.address == "49 rue Charras, Marseille"
        assert catalans.address_location == PARADIS.point
        assert catalans.contact_email == "catalans@example.com"
        assert "3 created" in output
        assert "705 BAD EMAIL" in output
        assert "704 PLACE 4 SEPTEMBRE: no address" in output
        # One reassignment for the whole import.
        assert reassignments(callbacks) == 1

    def test_running_again_updates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(geocoding, "_fetch", answers(PARADIS))
        run_import(write_csv(tmp_path), "--federation", "7")

        output = run_import(
            write_csv(tmp_path, CSV.replace("catalans@example.com", "new@example.com")),
            "--federation",
            "7",
        )

        assert NeighborhoodAssociation.objects.count() == 3
        assert NeighborhoodAssociation.objects.get(code="701").contact_email == "new@example.com"
        assert "0 created, 3 updated" in output

    def test_matches_associations_created_by_hand(self, tmp_path):
        manual = NeighborhoodAssociation.objects.create(name="Place 4 Septembre")

        run_import(write_csv(tmp_path), "--federation", "7")

        manual.refresh_from_db()
        assert manual.code == "704"
        assert NeighborhoodAssociation.objects.count() == 3

    def test_unlocated_when_service_is_down(self, tmp_path):
        output = run_import(write_csv(tmp_path), "--federation", "7")

        assert NeighborhoodAssociation.objects.get(code="701").address_location is None
        assert "701 PHARO – CATALANS: 49 rue Charras, Marseille" in output

    def test_dry_run_changes_nothing(self, tmp_path):
        output = run_import(write_csv(tmp_path), "--federation", "7", "--dry-run")

        assert not NeighborhoodAssociation.objects.exists()
        assert output.startswith("[dry run] 3 created")

    def test_no_row_of_the_federation(self, tmp_path):
        with pytest.raises(CommandError):
            run_import(write_csv(tmp_path), "--federation", "9")

    def test_missing_columns(self, tmp_path):
        with pytest.raises(CommandError):
            run_import(write_csv(tmp_path, "nom,adresse\nA,B\n"), "--federation", "7")


# --- declining ------------------------------------------------------------------


@pytest.mark.django_db
class TestDecliningAnAssociation:
    PROFILE = {
        "email": "resident@example.com",
        "first_name": "Res",
        "last_name": "Ident",
        "postal_code": "13007",
    }

    def test_declining_leaves_the_user_without_one(self, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, catalans, declined=True)

        assert resident.association is None
        assert resident.association_chosen

    def test_reassignment_respects_it(self, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, declined=True)
        resident.save()

        reassign_residents()

        resident.refresh_from_db()
        assert resident.association is None

    def test_deleting_an_association_respects_it(
        self, resident, catalans, auffes, django_capture_on_commit_callbacks
    ):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES, declined=True)
        resident.save()

        with django_capture_on_commit_callbacks(execute=True):
            catalans.delete()

        resident.refresh_from_db()
        assert (resident.association, resident.association_chosen) == (None, True)

    def test_profile_box(self, client, resident, catalans, auffes):
        set_address(resident, "Vallon des Auffes", HOME_NEAR_AUFFES)
        resident.save()
        client.force_login(resident)

        client.post(
            reverse("profile_edit"),
            {
                **self.PROFILE,
                "address": "Vallon des Auffes",
                "association": catalans.pk,
                "no_association": "on",
            },
        )
        resident.refresh_from_db()
        assert (resident.association, resident.association_chosen) == (None, True)
        assert client.get(reverse("profile_edit")).context["form"].initial["no_association"]

        # Unticking it follows the address again.
        client.post(reverse("profile_edit"), {**self.PROFILE, "address": "Vallon des Auffes"})
        resident.refresh_from_db()
        assert (resident.association, resident.association_chosen) == (auffes, False)

    def test_register_box(self, client, catalans):
        with patch("core.views.register.send_verification_email"):
            response = client.post(
                reverse("register"),
                {
                    **TestAssociationFields.REGISTRATION,
                    "address": "12 rue paradis",
                    "no_association": "on",
                },
            )

        assert response.status_code == 302
        user = User.objects.get(email="new@example.com")
        assert (user.association, user.association_chosen) == (None, True)
        client.logout()
        assert "data-no-association" in client.get(reverse("register")).content.decode()
