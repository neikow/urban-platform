from dataclasses import dataclass

from django.db import migrations

@dataclass
class _DistrictDefinition:
    name: str
    name_short: str
    neighborhoods: list[str]

def _populate_marseille_data(apps, schema_editor):
    City = apps.get_model("core", "City")
    CityDistrict = apps.get_model("core", "CityDistrict")
    CityNeighborhood = apps.get_model("core", "CityNeighborhood")

    marseille, _ = City.objects.get_or_create(name="Marseille")

    data = [
        _DistrictDefinition(
            name="1er Arrondissement",
            name_short="1er",
            neighborhoods=[
                "Belsunce",
                "Le Chapitre",
                "Noailles",
                "Opéra",
                "Saint-Charles",
                "Thiers",
            ],
        ),
        _DistrictDefinition(
            name="2ème Arrondissement",
            name_short="2ème",
            neighborhoods=[
                "Arenc",
                "Les Grands Carmes",
                "Hôtel de Ville",
                "La Joliette",
            ],
        ),
        # ... (remaining district definitions)
    ]

    for district_index, definition in enumerate(data):
        district, _ = CityDistrict.objects.get_or_create(
            name=definition.name, name_short=definition.name_short, city=marseille
        )
        for neighborhood_name in definition.neighborhoods:
            CityNeighborhood.objects.get_or_create(
                name=neighborhood_name,
                district=district,
                postal_code="1300{}".format(str(district_index + 1).zfill(2)),
            )

def _rollback_marseille_data(apps, schema_editor):
    City = apps.get_model("core", "City")
    City.objects.filter(name="Marseille").delete()

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_populate_marseille_data, _rollback_marseille_data),
    ]
