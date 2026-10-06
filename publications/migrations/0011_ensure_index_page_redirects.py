from django.db import migrations

# Migration 0010 crashed mid-deploy on an environment with real (long) production
# slugs: Wagtail's automatic redirect creation on slug change failed to bulk_create
# a redirect for a descendant page whose path exceeded old_path's 255-char limit.
# The rename/move itself commits before that redirect-creation signal fires (it
# runs via transaction.on_commit), and it's ambiguous whether Django recorded 0010
# as applied before the exception escaped. This migration is a standalone,
# idempotent safety net: it just ensures the two index-page redirects exist,
# regardless of 0010's bookkeeping state or how far it got.


def ensure_redirects(apps, schema_editor):
    from pedagogy.models.pedagogy_index import PedagogyIndexPage
    from publications.models.publication_index import PublicationIndexPage
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.models import Site

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()

    publications_page = PublicationIndexPage.objects.filter(
        slug__in=["actualites", "publications"]
    ).first()
    pedagogy_page = PedagogyIndexPage.objects.filter(
        slug__in=["informations-utiles", "fiches-pedagogiques"]
    ).first()

    for old_path, page in (
        ("/publications", publications_page),
        ("/fiches-pedagogiques", pedagogy_page),
    ):
        if page is None:
            continue
        Redirect.objects.get_or_create(
            old_path=old_path,
            site=site,
            defaults={
                "redirect_page": page,
                "is_permanent": True,
                "automatically_created": True,
            },
        )


def reverse_ensure_redirects(apps, schema_editor):
    from wagtail.contrib.redirects.models import Redirect

    Redirect.objects.filter(old_path__in=["/publications", "/fiches-pedagogiques"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0010_rename_and_reorder_publications_pedagogy"),
    ]

    operations = [
        migrations.RunPython(
            code=ensure_redirects,
            reverse_code=reverse_ensure_redirects,
        )
    ]
