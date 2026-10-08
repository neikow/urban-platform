"""Keep the existing website on its area: before the Territory setting, the
7th arrondissement of Marseille was written in the code.

Only for a database already in use: a new website starts without a territory
and is given one when installed (``manage.py configure_territory``).
"""

import json
from pathlib import Path

from django.db import migrations

BOUNDARY = Path(__file__).resolve().parent.parent / "fixtures" / "marseille-7e.geojson"


def seed(apps, schema_editor):
    User = apps.get_model("core", "User")
    Territory = apps.get_model("core", "Territory")
    if not User.objects.exists() or Territory.objects.exists():
        return
    Territory.objects.create(
        name="7e arrondissement de Marseille",
        name_in="dans le 7e arrondissement de Marseille",
        city_name="Marseille",
        city_code="13055",
        postal_codes="13007",
        boundary=json.loads(BOUNDARY.read_text())["geometry"],
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0020_territory")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
