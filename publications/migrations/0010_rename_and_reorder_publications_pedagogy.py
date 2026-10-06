from django.db import migrations

# Wagtail auto-creates a Redirect for every live descendant on slug change/page move
# (WAGTAILREDIRECTS_AUTO_CREATE, default True). Redirect.old_path is a 255-char
# CharField; with this project's real (long, deeply-nested) production slugs that
# bulk_create can overflow the column and crash the migration mid-deploy. We
# disconnect those signal receivers before the rename/move and instead create just
# the two index-page redirects ourselves, which are guaranteed short.
#
# We deliberately do NOT reconnect the signals: page_slug_changed/post_page_move
# are sent via transaction.on_commit, i.e. only once this migration's outer
# transaction actually commits — reconnecting synchronously here would restore
# the receiver before that commit-time send() fires, defeating the disconnect.
# Migrations run in their own one-shot process (this project's "migrator"
# service, separate from web/worker), so leaving the signal disconnected for the
# rest of this process's short lifetime is harmless.
#
# Lookups use slug__in=[old, new] so this is safe to re-run: the DML in this
# function commits before Wagtail's redirect-creation hook used to fire (it runs
# via transaction.on_commit), so a prior crashed attempt may have already
# committed the rename/move while leaving the redirects uncreated.


def _ensure_redirect(Redirect, site, old_path, page):
    Redirect.objects.get_or_create(
        old_path=old_path,
        site=site,
        defaults={
            "redirect_page": page,
            "is_permanent": True,
            "automatically_created": True,
        },
    )


def rename_and_reorder_pages(apps, schema_editor):
    from pedagogy.models.pedagogy_index import PedagogyIndexPage
    from publications.models.publication_index import PublicationIndexPage
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.contrib.redirects.signal_handlers import (
        autocreate_redirects_on_page_move,
        autocreate_redirects_on_slug_change,
    )
    from wagtail.models import Site
    from wagtail.signals import page_slug_changed, post_page_move

    publications_page = PublicationIndexPage.objects.filter(
        slug__in=["publications", "actualites"]
    ).first()
    pedagogy_page = PedagogyIndexPage.objects.filter(
        slug__in=["fiches-pedagogiques", "informations-utiles"]
    ).first()

    if publications_page is None or pedagogy_page is None:
        return

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()

    page_slug_changed.disconnect(autocreate_redirects_on_slug_change)
    post_page_move.disconnect(autocreate_redirects_on_page_move)

    # Reorder: Actualités (ex-Publications) should appear before Informations
    # utiles (ex-Fiches pédagogiques) in the frontend nav, which follows
    # tree/path order. Safe to call even if already in this relative order.
    publications_page.move(pedagogy_page, pos="left")

    publications_page.refresh_from_db()
    publications_page.title = "Actualités"
    publications_page.draft_title = "Actualités"
    publications_page.slug = "actualites"
    publications_page.save()
    publications_page.save_revision().publish()

    pedagogy_page.refresh_from_db()
    pedagogy_page.title = "Informations utiles"
    pedagogy_page.draft_title = "Informations utiles"
    pedagogy_page.slug = "informations-utiles"
    pedagogy_page.save()
    pedagogy_page.save_revision().publish()

    _ensure_redirect(Redirect, site, "/publications", publications_page)
    _ensure_redirect(Redirect, site, "/fiches-pedagogiques", pedagogy_page)


def reverse_rename_and_reorder_pages(apps, schema_editor):
    from legal.models.legal_index import LegalIndexPage
    from pedagogy.models.pedagogy_index import PedagogyIndexPage
    from publications.models.publication_index import PublicationIndexPage
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.contrib.redirects.signal_handlers import (
        autocreate_redirects_on_page_move,
        autocreate_redirects_on_slug_change,
    )
    from wagtail.signals import page_slug_changed, post_page_move

    Redirect.objects.filter(old_path__in=["/publications", "/fiches-pedagogiques"]).delete()

    publications_page = PublicationIndexPage.objects.filter(
        slug__in=["actualites", "publications"]
    ).first()
    pedagogy_page = PedagogyIndexPage.objects.filter(
        slug__in=["informations-utiles", "fiches-pedagogiques"]
    ).first()
    legal_page = LegalIndexPage.objects.first()

    if publications_page is None or pedagogy_page is None:
        return

    page_slug_changed.disconnect(autocreate_redirects_on_slug_change)
    post_page_move.disconnect(autocreate_redirects_on_page_move)

    if legal_page is not None:
        publications_page.move(legal_page, pos="right")

    publications_page.refresh_from_db()
    publications_page.title = "Publications"
    publications_page.draft_title = "Publications"
    publications_page.slug = "publications"
    publications_page.save()
    publications_page.save_revision().publish()

    pedagogy_page.refresh_from_db()
    pedagogy_page.title = "Fiches pédagogiques"
    pedagogy_page.draft_title = "Fiches pédagogiques"
    pedagogy_page.slug = "fiches-pedagogiques"
    pedagogy_page.save()
    pedagogy_page.save_revision().publish()


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0009_remove_projectpage_enable_voting_and_more"),
        ("pedagogy", "0013_alter_pedagogycardpage_content"),
        ("legal", "0008_codeofconductconsent"),
        ("wagtailredirects", "0008_add_verbose_name_plural"),
    ]

    operations = [
        migrations.RunPython(
            code=rename_and_reorder_pages,
            reverse_code=reverse_rename_and_reorder_pages,
        )
    ]
