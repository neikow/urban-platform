from django.db import migrations
from treebeard.mp_tree import MP_Node

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


def index_pages(model_name):
    """Index pages as plain wagtail Pages: the current specific models may have
    columns that do not exist yet when this migration runs."""
    from wagtail.models import Page

    return Page.objects.filter(content_type__model=model_name)


def rename(page, title, slug):
    """Page.save() loads the specific page: update the row and the url_paths directly."""
    page.refresh_from_db()
    old_url_path = page.url_path
    page.title = page.draft_title = title
    page.slug = slug
    page.set_url_path(page.get_parent())
    type(page).objects.filter(pk=page.pk).update(
        title=title, draft_title=title, slug=slug, url_path=page.url_path
    )
    page._update_descendant_url_paths(old_url_path, page.url_path)


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
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.contrib.redirects.signal_handlers import (
        autocreate_redirects_on_page_move,
        autocreate_redirects_on_slug_change,
    )
    from wagtail.models import Site
    from wagtail.signals import page_slug_changed, post_page_move

    publications_page = (
        index_pages("publicationindexpage").filter(slug__in=["publications", "actualites"]).first()
    )
    pedagogy_page = (
        index_pages("pedagogyindexpage")
        .filter(slug__in=["fiches-pedagogiques", "informations-utiles"])
        .first()
    )

    if publications_page is None or pedagogy_page is None:
        return

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()

    page_slug_changed.disconnect(autocreate_redirects_on_slug_change)
    post_page_move.disconnect(autocreate_redirects_on_page_move)

    # Reorder: Actualités (ex-Publications) should appear before Informations
    # utiles (ex-Fiches pédagogiques) in the frontend nav, which follows
    # tree/path order. Safe to call even if already in this relative order.
    # treebeard's move: Wagtail's loads the specific page. Same parent, so the
    # url_paths do not change.
    MP_Node.move(publications_page, pedagogy_page, pos="left")

    rename(publications_page, "Actualités", "actualites")

    rename(pedagogy_page, "Informations utiles", "informations-utiles")

    _ensure_redirect(Redirect, site, "/publications", publications_page)
    _ensure_redirect(Redirect, site, "/fiches-pedagogiques", pedagogy_page)


def reverse_rename_and_reorder_pages(apps, schema_editor):
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.contrib.redirects.signal_handlers import (
        autocreate_redirects_on_page_move,
        autocreate_redirects_on_slug_change,
    )
    from wagtail.signals import page_slug_changed, post_page_move

    Redirect.objects.filter(old_path__in=["/publications", "/fiches-pedagogiques"]).delete()

    publications_page = (
        index_pages("publicationindexpage").filter(slug__in=["actualites", "publications"]).first()
    )
    pedagogy_page = (
        index_pages("pedagogyindexpage")
        .filter(slug__in=["informations-utiles", "fiches-pedagogiques"])
        .first()
    )
    legal_page = index_pages("legalindexpage").first()

    if publications_page is None or pedagogy_page is None:
        return

    page_slug_changed.disconnect(autocreate_redirects_on_slug_change)
    post_page_move.disconnect(autocreate_redirects_on_page_move)

    if legal_page is not None:
        MP_Node.move(publications_page, legal_page, pos="right")

    rename(publications_page, "Publications", "publications")

    rename(pedagogy_page, "Fiches pédagogiques", "fiches-pedagogiques")


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
