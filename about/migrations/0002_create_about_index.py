from django.db import migrations

_ABOUT_INDEX_SLUG = "a-propos"


def _create_about_index(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    AboutIndexPage = apps.get_model("about", "AboutIndexPage")
    HomePage = apps.get_model("home", "HomePage")
    Page = apps.get_model("wagtailcore", "Page")

    if AboutIndexPage.objects.filter(slug=_ABOUT_INDEX_SLUG).exists():
        return

    about_index_content_type, __ = ContentType.objects.get_or_create(
        model="aboutindexpage", app_label="about"
    )

    home_page = HomePage.objects.first()
    if not home_page:
        raise ValueError("No HomePage found. Cannot create AboutIndexPage.")

    # Get the last child of the homepage to determine the next path
    children = Page.objects.filter(
        path__startswith=home_page.path, depth=home_page.depth + 1
    ).order_by("path")
    last_child = children.last()

    if last_child:
        path_len = len(last_child.path)
        last_path_int = int(last_child.path[path_len - 4 :])
        new_suffix = f"{last_path_int + 1:04d}"
        new_path = last_child.path[:-4] + new_suffix
    else:
        new_path = home_page.path + "0001"

    AboutIndexPage.objects.create(
        title="À propos",
        draft_title="À propos",
        slug=_ABOUT_INDEX_SLUG,
        content_type=about_index_content_type,
        path=new_path,
        depth=home_page.depth + 1,
        numchild=0,
        url_path=home_page.url_path + _ABOUT_INDEX_SLUG + "/",
        locale_id=home_page.locale_id,
        live=True,
        show_in_menus=False,
    )

    home_page.numchild += 1
    home_page.save(update_fields=["numchild"])


def _remove_about_index(apps, schema_editor):
    AboutIndexPage = apps.get_model("about", "AboutIndexPage")
    HomePage = apps.get_model("home", "HomePage")

    page = AboutIndexPage.objects.filter(slug=_ABOUT_INDEX_SLUG).first()
    if page:
        parent_path = page.path[:-4]
        parent = HomePage.objects.filter(path=parent_path).first()
        if parent:
            parent.numchild = max(0, parent.numchild - 1)
            parent.save(update_fields=["numchild"])
        page.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("about", "0001_initial"),
        ("home", "0002_create_homepage"),
        ("wagtailcore", "0040_page_draft_title"),
    ]

    operations = [
        migrations.RunPython(_create_about_index, _remove_about_index),
    ]
