from django.db import migrations

_ABOUT_INDEX_SLUG = "a-propos"

_ABOUT_PAGES = [
    {
        "model_name": "aboutwebsitepage",
        "app_label": "about",
        "title": "La plateforme",
        "slug": "la-plateforme",
    },
    {
        "model_name": "aboutcommissionpage",
        "app_label": "about",
        "title": "La commission urbanisme",
        "slug": "commission-urbanisme",
    },
    {
        "model_name": "aboutdevteampage",
        "app_label": "about",
        "title": "L'équipe de développement",
        "slug": "equipe-de-developpement",
    },
]


def _create_about_pages(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    AboutIndexPage = apps.get_model("about", "AboutIndexPage")
    Page = apps.get_model("wagtailcore", "Page")

    about_index = AboutIndexPage.objects.filter(slug=_ABOUT_INDEX_SLUG).first()
    if not about_index:
        about_index = AboutIndexPage.objects.first()
        if not about_index:
            print("AboutIndexPage not found. Cannot create about pages.")
            return

    for page_def in _ABOUT_PAGES:
        model_class = apps.get_model(page_def["app_label"], page_def["model_name"])

        if model_class.objects.filter(slug=page_def["slug"]).exists():
            continue

        content_type, __ = ContentType.objects.get_or_create(
            model=page_def["model_name"], app_label=page_def["app_label"]
        )

        children = Page.objects.filter(
            path__startswith=about_index.path, depth=about_index.depth + 1
        ).order_by("path")
        last_child = children.last()

        if last_child:
            path_len = len(last_child.path)
            last_path_int = int(last_child.path[path_len - 4 :])
            new_suffix = f"{last_path_int + 1:04d}"
            new_path = last_child.path[:-4] + new_suffix
        else:
            new_path = about_index.path + "0001"

        model_class.objects.create(
            title=page_def["title"],
            draft_title=page_def["title"],
            slug=page_def["slug"],
            content_type=content_type,
            path=new_path,
            depth=about_index.depth + 1,
            numchild=0,
            url_path=about_index.url_path + page_def["slug"] + "/",
            locale_id=about_index.locale_id,
            live=True,
            show_in_menus=True,
        )

        about_index.numchild += 1
        about_index.save(update_fields=["numchild"])


def _remove_about_pages(apps, schema_editor):
    AboutIndexPage = apps.get_model("about", "AboutIndexPage")

    for page_def in _ABOUT_PAGES:
        model_class = apps.get_model(page_def["app_label"], page_def["model_name"])
        page = model_class.objects.filter(slug=page_def["slug"]).first()
        if page:
            parent_path = page.path[:-4]
            parent = AboutIndexPage.objects.filter(path=parent_path).first()
            if parent:
                parent.numchild = max(0, parent.numchild - 1)
                parent.save(update_fields=["numchild"])
            page.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("about", "0002_create_about_index"),
    ]

    operations = [
        migrations.RunPython(_create_about_pages, _remove_about_pages),
    ]
