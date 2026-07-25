from django.db import migrations

# Wagtail auto-creates redirects on slug change and page move
# (WAGTAILREDIRECTS_AUTO_CREATE, default True, not overridden in this project),
# so old URLs are handled automatically — no manual Redirect bookkeeping needed here.


def rename_and_reorder_pages(apps, schema_editor):
    from pedagogy.models.pedagogy_index import PedagogyIndexPage
    from publications.models.publication_index import PublicationIndexPage

    publications_page = PublicationIndexPage.objects.filter(slug="publications").first()
    pedagogy_page = PedagogyIndexPage.objects.filter(slug="fiches-pedagogiques").first()

    if publications_page is None or pedagogy_page is None:
        return

    # Reorder: Actualités (ex-Publications) should appear before Informations utiles
    # (ex-Fiches pédagogiques) in the frontend nav, which follows tree/path order.
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


def reverse_rename_and_reorder_pages(apps, schema_editor):
    from legal.models.legal_index import LegalIndexPage
    from pedagogy.models.pedagogy_index import PedagogyIndexPage
    from publications.models.publication_index import PublicationIndexPage

    publications_page = PublicationIndexPage.objects.filter(slug="actualites").first()
    pedagogy_page = PedagogyIndexPage.objects.filter(slug="informations-utiles").first()
    legal_page = LegalIndexPage.objects.first()

    if publications_page is None or pedagogy_page is None:
        return

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
        # Renaming/moving pages fires Wagtail's page_slug_changed / post_page_move
        # signals, which auto-create redirects — the redirects table must exist first.
        ("wagtailredirects", "0008_add_verbose_name_plural"),
    ]

    operations = [
        migrations.RunPython(
            code=rename_and_reorder_pages,
            reverse_code=reverse_rename_and_reorder_pages,
        )
    ]
