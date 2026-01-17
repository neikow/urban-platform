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

    data = [_DistrictDefinition(
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
        _DistrictDefinition(
            name="3ème Arrondissement",
            name_short="3ème",
            neighborhoods=[
                "Belle de Mai",
                "Saint-Lazare",
                "Saint-Mauront",
                "La Villette",
            ],
        ),
        _DistrictDefinition(
            name="4ème Arrondissement",
            name_short="4ème",
            neighborhoods=[
                "La Blancarde",
                "Les Chartreux",
                "Chutes-Lavie",
                "Cinq-Avenues",
            ],
        ),
        _DistrictDefinition(
            name="5ème Arrondissement",
            name_short="5ème",
            neighborhoods=["Baille", "Le Camas", "La Conception", "Saint-Pierre"],
        ),
        _DistrictDefinition(
            name="6ème Arrondissement",
            name_short="6ème",
            neighborhoods=[
                "Castellane",
                "Lodi",
                "Notre-Dame du Mont",
                "Palais de Justice",
                "Préfecture",
                "Vauban",
            ],
        ),
        _DistrictDefinition(
            name="7ème Arrondissement",
            name_short="7ème",
            neighborhoods=[
                "Bompard",
                "Endoume",
                "Les Îles",
                "Le Pharo",
                "Le Roucas Blanc",
                "Saint-Lambert",
                "Saint-Victor",
            ],
        ),
        _DistrictDefinition(
            name="8ème Arrondissement",
            name_short="8ème",
            neighborhoods=[
                "Bonneveine",
                "Les Goudes",
                "Montredon",
                "Périer",
                "La Plage",
                "La Pointe Rouge",
                "Le Rouet",
                "Sainte-Anne",
                "Saint-Giniez",
                "Vieille Chapelle",
            ],
        ),
        _DistrictDefinition(
            name="9ème Arrondissement",
            name_short="9ème",
            neighborhoods=[
                "Les Baumettes",
                "Le Cabot",
                "Carpiagne",
                "Mazargues",
                "La Panouse",
                "Le Redon",
                "Sainte-Marguerite",
                "Sormiou",
                "Vaufrèges",
            ],
        ),
        _DistrictDefinition(
            name="10ème Arrondissement",
            name_short="10ème",
            neighborhoods=[
                "La Capelette",
                "Menpenti",
                "Pont-de-Vivaux",
                "Saint-Loup",
                "Saint-Tronc",
                "La Timone",
            ],
        ),
        _DistrictDefinition(
            name="11ème Arrondissement",
            name_short="11ème",
            neighborhoods=[
                "Les Accates",
                "La Barasse",
                "Les Camoins",
                "Éoures",
                "La Millière",
                "La Pomme",
                "Saint-Marcel",
                "Saint-Menet",
                "La Treille",
                "La Valbarelle",
                "La Valentine",
            ],
        ),
        _DistrictDefinition(
            name="12ème Arrondissement",
            name_short="12ème",
            neighborhoods=[
                "Les Caillols",
                "La Fourragère",
                "Montolivet",
                "Saint-Barnabé",
                "Saint-Jean du Désert",
                "Saint-Julien",
                "Les Trois-Lucs",
            ],
        ),
        _DistrictDefinition(
            name="13ème Arrondissement",
            name_short="13ème",
            neighborhoods=[
                "Château Gombert",
                "La Croix-Rouge",
                "Malpassé",
                "Les Médecins",
                "Les Mourets",
                "Les Olives",
                "Palama",
                "La Rose",
                "Saint-Jérôme",
                "Saint-Just",
                "Saint-Mitre",
            ],
        ),
        _DistrictDefinition(
            name="14ème Arrondissement",
            name_short="14ème",
            neighborhoods=[
                "Les Arnavaux",
                "Bon-Secours",
                "Le Canet",
                "Le Merlan",
                "Saint-Barthélémy",
                "Saint-Joseph",
                "Sainte-Marthe",
            ],
        ),
        _DistrictDefinition(
            name="15ème Arrondissement",
            name_short="15ème",
            neighborhoods=[
                "Les Aygalades",
                "Les Borels",
                "La Cabucelle",
                "La Calade",
                "Les Crottes",
                "La Delorme",
                "Notre-Dame Limite",
                "Saint-Antoine",
                "Saint-Louis",
                "Verduron",
                "La Viste",
            ],
        ),
        _DistrictDefinition(
            name="16ème Arrondissement",
            name_short="16ème",
            neighborhoods=[
                "L'Estaque",
                "Les Riaux",
                "Saint-André",
                "Saint-Henri"],
        ),
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
