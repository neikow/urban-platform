from django.db import migrations
from django.utils.text import slugify
from pedagogy.utils.pedagogy_index_page import create_pedagogy_index_page

_PEDAGOGY_CARDS_SLUG = "fiches-pedagogiques"


def _create_pedagogy_index(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    PedagogyIndexPage = apps.get_model("pedagogy", "PedagogyIndexPage")
    HomePage = apps.get_model("home", "HomePage")
    Page = apps.get_model("wagtailcore", "Page")

    if PedagogyIndexPage.objects.filter(slug=_PEDAGOGY_CARDS_SLUG).exists():
        return

    pedagogy_index_page_content_type, __ = ContentType.objects.get_or_create(
        model="pedagogyindexpage", app_label="pedagogy"
    )

    home_page = HomePage.objects.first()
    if not home_page:
        raise ValueError("No HomePage found. Cannot create PedagogyIndexPage.")

    # Get the last child of the homepage to determine the next path
    children = Page.objects.filter(
        path__startswith=home_page.path, depth=home_page.depth + 1
    ).order_by("path")
    last_child = children.last()

    if last_child:
        # If children exist, increment the last child's path
        path_len = len(last_child.path)
        last_path_int = int(last_child.path[path_len - 4 :])
        new_suffix = f"{last_path_int + 1:04d}"
        new_path = last_child.path[:-4] + new_suffix
    else:
        # If no children, append '0001' to parent path
        new_path = home_page.path + "0001"

    PedagogyIndexPage.objects.create(
        title="Fiches pédagogiques",
        draft_title="Fiches pédagogiques",
        slug=_PEDAGOGY_CARDS_SLUG,
        content_type=pedagogy_index_page_content_type,
        path=new_path,
        depth=home_page.depth + 1,
        numchild=0,
        url_path=home_page.url_path + _PEDAGOGY_CARDS_SLUG + "/",
        locale_id=home_page.locale_id,
        live=True,
        show_in_menus=True,
    )

    home_page.numchild += 1
    home_page.save(update_fields=["numchild"])


def _remove_pedagogy_index(apps, schema_editor):
    PedagogyIndexPage = apps.get_model("pedagogy", "PedagogyIndexPage")
    HomePage = apps.get_model("home", "HomePage")

    page = PedagogyIndexPage.objects.filter(slug=_PEDAGOGY_CARDS_SLUG).first()
    if page:
        # Note: Finding parent via path prefix is safer in migrations
        parent_path = page.path[:-4]
        parent = HomePage.objects.filter(path=parent_path).first()
        if parent:
            parent.numchild = max(0, parent.numchild - 1)
            parent.save(update_fields=["numchild"])
        page.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogy", "0001_initial"),
        ("home", "0002_create_homepage"),
        ("wagtailcore", "0040_page_draft_title"),
    ]

    operations = [
        migrations.RunPython(_create_pedagogy_index, _remove_pedagogy_index),
    ]
