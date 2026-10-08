from django.db import migrations, models


def code_marseille_7e(apps, schema_editor):
    """The territory seeded by 0021 is the 7th arrondissement of Marseille (INSEE 13207)."""
    Territory = apps.get_model("core", "Territory")
    Territory.objects.filter(code="", city_code="13055", postal_codes="13007").update(code="13207")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_branding_marseille_7e"),
    ]

    operations = [
        migrations.AddField(
            model_name="territory",
            name="code",
            field=models.CharField(
                blank=True, editable=False, max_length=5, verbose_name="INSEE code"
            ),
        ),
        migrations.RunPython(code_marseille_7e, migrations.RunPython.noop),
    ]
