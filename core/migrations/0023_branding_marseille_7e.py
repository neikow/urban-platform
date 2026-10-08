"""Keep the existing website's sign-up photo and contact: they were written in
the code (a static photo of Endoume, the federation's address in the starter
texts) before the Branding setting.

Only for a database already in use, like the territory (0021).
"""

import hashlib
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations
from PIL import Image as PILImage

PHOTO = Path(__file__).resolve().parent.parent / "fixtures" / "endoume-marseille.jpg"


def seed(apps, schema_editor):
    User = apps.get_model("core", "User")
    Branding = apps.get_model("core", "Branding")
    Image = apps.get_model("wagtailimages", "Image")
    Collection = apps.get_model("wagtailcore", "Collection")
    if not User.objects.exists() or Branding.objects.exists():
        return

    with PILImage.open(PHOTO) as photo:
        width, height = photo.size
    data = PHOTO.read_bytes()
    image = Image(
        title="Endoume, Marseille",
        width=width,
        height=height,
        file_size=len(data),
        file_hash=hashlib.sha1(data, usedforsecurity=False).hexdigest(),
        collection=Collection.objects.filter(depth=1).first(),
    )
    # Historical models lack Image.get_upload_to: stored where Wagtail would put it.
    with PHOTO.open("rb") as handle:
        image.file = default_storage.save(f"original_images/{PHOTO.name}", File(handle))
    image.save()

    Branding.objects.create(contact_email="fedeciqmarseille7@hotmail.fr", signup_image=image)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0022_branding"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
