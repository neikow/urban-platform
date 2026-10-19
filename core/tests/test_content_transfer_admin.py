"""Copying content between sites: archive checks, import modes, jobs and the admin page."""

import io
import json
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.images.models import Image

from core.content_transfer.archive import (
    MANIFEST_NAME,
    SIGNATURE_NAME,
    ArchiveError,
    open_archive,
    remap_media_ids,
    sha256_bytes,
    sign,
)
from core.content_transfer.exporter import export_archive
from core.content_transfer.importer import import_archive
from core.content_transfer.jobs import prune_archives, run_export, run_import
from core.models import ContentTransfer, ContentTransferKind, ContentTransferStatus, User, UserRole
from core.tests.utils.factories import ImageFactory
from home.models import HomePage
from publications.factories import ProjectPageFactory
from publications.models.project import ProjectPage
from publications.models.publication_index import PublicationIndexPage

KEY = "a-shared-transfer-key"


@pytest.fixture(autouse=True)
def media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.CONTENT_TRANSFER_KEY = KEY
    settings.CONTENT_IMPORT_ENABLED = True
    return settings.MEDIA_ROOT


@pytest.fixture
def project(db):
    image = ImageFactory.create()
    return ProjectPageFactory.create(
        parent=PublicationIndexPage.objects.get(),
        title="Mobilité douce",
        slug="mobilite-douce",
        hero_image=image,
    )


def exported(**kwargs) -> io.BytesIO:
    output = io.BytesIO()
    export_archive(output, log=lambda message: None, **kwargs)
    output.seek(0)
    return output


def rewrite(archive: io.BytesIO, change) -> io.BytesIO:
    """A copy of the archive with ``change(name, data)`` applied to each member."""
    source = zipfile.ZipFile(archive)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as target:
        for info in source.infolist():
            result = change(info.filename, source.read(info.filename))
            if result is not None:
                name, data = result
                target.writestr(name, data)
    output.seek(0)
    return output


# --- archive checks -------------------------------------------------------------


@pytest.mark.django_db
class TestArchiveChecks:
    def test_signed_archive_opens(self, project):
        archive, manifest = open_archive(exported(key=KEY), KEY)

        assert SIGNATURE_NAME in archive.namelist()
        assert [p["slug"] for p in manifest["pages"] if p["model"] != "home.homepage"] == [
            "mobilite-douce"
        ]

    def test_unsigned_archive_is_refused(self, project):
        with pytest.raises(ArchiveError, match="not signed"):
            open_archive(exported(), KEY)

    def test_other_key_is_refused(self, project):
        with pytest.raises(ArchiveError, match="signature"):
            open_archive(exported(key="another-site"), KEY)

    def test_changed_manifest_is_refused(self, project):
        def change(name, data):
            if name == MANIFEST_NAME:
                return name, data.replace(b"Mobilit\xc3\xa9 douce", b"Changed")
            return name, data

        with pytest.raises(ArchiveError, match="signature"):
            open_archive(rewrite(exported(key=KEY), change), KEY)

    def test_changed_media_file_is_refused_on_import(self, project):
        def change(name, data):
            return (
                (name, b"not the same image") if name.startswith("media/images/") else (name, data)
            )

        with pytest.raises(ArchiveError, match="checksum"):
            import_archive(rewrite(exported(key=KEY), change), key=KEY, log=lambda m: None)

    def forged(self, manifest_change=None, extra=None) -> io.BytesIO:
        manifest = {"version": 1, "images": [], "documents": [], "pages": []}
        if manifest_change:
            manifest_change(manifest)
        raw = json.dumps(manifest).encode()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(MANIFEST_NAME, raw)
            archive.writestr(SIGNATURE_NAME, sign(raw, KEY))
            for name, data in (extra or {}).items():
                archive.writestr(name, data)
        output.seek(0)
        return output

    def test_unsafe_names_are_refused(self, db):
        with pytest.raises(ArchiveError, match="Unsafe"):
            open_archive(self.forged(extra={"../../etc/passwd": b"x"}), KEY)

    def test_other_page_types_are_refused(self, db):
        def change(manifest):
            manifest["pages"].append({"model": "core.user", "parent_model": None})

        with pytest.raises(ArchiveError, match="not allowed"):
            open_archive(self.forged(change), KEY)

    def test_other_file_types_are_refused(self, db):
        def change(manifest):
            manifest["documents"].append(
                {
                    "pk": 1,
                    "file": "media/documents/1__evil.html",
                    "filename": "evil.html",
                    "sha256": "x",
                }
            )

        with pytest.raises(ArchiveError, match="not allowed"):
            open_archive(self.forged(change, {"media/documents/1__evil.html": b"<script>"}), KEY)

    def test_not_a_zip(self, db):
        with pytest.raises(ArchiveError):
            open_archive(io.BytesIO(b"hello"), KEY)


class TestRemapMediaIds:
    def test_struct_keys_and_rich_text(self):
        raw = [
            {"type": "image", "value": {"image": 5, "caption": "x"}},
            {"type": "doc", "value": {"document": 7}},
            {
                "type": "rich_text",
                "value": '<p><embed embedtype="image" id="5" format="left"/>'
                '<a linktype="document" id="7">pdf</a><a linktype="page" id="5">page</a></p>',
            },
        ]

        result = remap_media_ids(raw, {5: 50}, {7: 70})

        assert result[0]["value"]["image"] == 50
        assert result[1]["value"]["document"] == 70
        html = result[2]["value"]
        assert 'embedtype="image" id="50"' in html
        assert 'linktype="document" id="70"' in html
        assert 'linktype="page" id="5"' in html  # pages are not media


# --- import modes ---------------------------------------------------------------


@pytest.mark.django_db
class TestImportModes:
    def test_replace_updates_in_place(self, project):
        archive = exported(key=KEY)
        ProjectPage.objects.filter(pk=project.pk).update(title="Changed here")

        counts = import_archive(archive, mode="replace", key=KEY, log=lambda m: None)

        assert ProjectPage.objects.get(pk=project.pk).title == "Mobilité douce"
        assert ProjectPage.objects.count() == 1
        assert counts["pages_updated"] >= 2  # the project and the home page

    def test_create_adds_new_pages_and_keeps_the_home_page(self, project):
        home = HomePage.objects.get()
        archive = exported(key=KEY)
        images_before = Image.objects.count()
        messages: list[str] = []

        counts = import_archive(archive, mode="create", key=KEY, log=messages.append)

        slugs = sorted(ProjectPage.objects.values_list("slug", flat=True))
        assert slugs == ["mobilite-douce", "mobilite-douce-2"]
        assert ProjectPage.objects.get(slug="mobilite-douce").pk == project.pk
        assert counts["pages_created"] == 1
        assert counts["pages_skipped"] == 1
        assert HomePage.objects.get().latest_revision_id == home.latest_revision_id
        assert messages
        # The same images are already here: they are reused, not copied.
        assert counts["media_kept"] >= 1
        assert counts["media_created"] == 0
        assert Image.objects.count() == images_before

    def test_create_gives_a_new_id_to_a_media_whose_id_is_taken(self, project):
        archive = exported(key=KEY)
        original = project.hero_image
        # Here, that id now holds another file.
        original.file.save("other.png", ContentFile(b"another file"), save=False)
        original.width = original.height = 1
        original.save()
        images_before = Image.objects.count()

        counts = import_archive(archive, mode="create", key=KEY, log=lambda m: None)

        assert counts["media_created"] == 1
        copy = ProjectPage.objects.get(slug="mobilite-douce-2")
        assert copy.hero_image_id not in (None, original.pk)
        assert Image.objects.count() == images_before + 1
        assert sha256_bytes(copy.hero_image.file.read()) != sha256_bytes(b"another file")


# --- jobs -----------------------------------------------------------------------


@pytest.mark.django_db
class TestJobs:
    def test_export_job_stores_a_private_archive(self, project, media):
        job = ContentTransfer.objects.create(kind=ContentTransferKind.EXPORT)

        run_export(job)

        job.refresh_from_db()
        assert job.status == ContentTransferStatus.DONE
        assert job.summary["pages"] >= 1
        path = Path(job.archive.path)
        assert path.is_relative_to(media / "transfers")
        assert path.name.startswith("export-") and len(path.stem) > 30
        open_archive(path, KEY)[0].close()

    def import_job(self, data: bytes, mode: str = "create") -> ContentTransfer:
        job = ContentTransfer(kind=ContentTransferKind.IMPORT, mode=mode)
        job.archive.save("upload.zip", SimpleUploadedFile("upload.zip", data), save=False)
        job.save()
        return job

    def test_import_job(self, project):
        job = self.import_job(exported(key=KEY).getvalue())

        run_import(job)

        job.refresh_from_db()
        assert job.status == ContentTransferStatus.DONE
        assert job.summary["pages_created"] == 1

    def test_failed_import_is_recorded(self, project):
        job = self.import_job(exported().getvalue())  # unsigned

        run_import(job)

        job.refresh_from_db()
        assert job.status == ContentTransferStatus.FAILED
        assert "not signed" in job.error
        assert ProjectPage.objects.count() == 1

    def test_import_disabled(self, project, settings):
        settings.CONTENT_IMPORT_ENABLED = False
        job = self.import_job(exported(key=KEY).getvalue())

        run_import(job)

        job.refresh_from_db()
        assert job.status == ContentTransferStatus.FAILED

    def test_a_job_runs_once(self, project):
        job = self.import_job(exported(key=KEY).getvalue())
        run_import(job)
        run_import(ContentTransfer.objects.get(pk=job.pk))

        assert ProjectPage.objects.count() == 2

    def test_prune(self, project):
        job = ContentTransfer.objects.create(kind=ContentTransferKind.EXPORT)
        run_export(job)
        job.refresh_from_db()
        path = Path(job.archive.path)
        ContentTransfer.objects.filter(pk=job.pk).update(
            created_at=timezone.now() - timedelta(days=8)
        )

        assert prune_archives() == 1
        assert not path.exists()
        assert not ContentTransfer.objects.exists()


# --- admin page -----------------------------------------------------------------


def make_user(email: str, **kwargs) -> User:
    return User.objects.create_user(email=email, password="Password123", **kwargs)


@pytest.fixture
def superuser(db):
    return make_user("root@example.com", is_superuser=True, role=UserRole.ADMIN)


@pytest.mark.django_db
class TestAdminPage:
    def test_superusers_only(self, client, superuser):
        administrator = make_user("admin@example.com", role=UserRole.ADMIN)
        client.force_login(administrator)
        assert client.get(reverse("admin_content_transfer")).status_code in (302, 403)
        assert client.post(reverse("admin_content_transfer_export")).status_code in (302, 403)
        assert not ContentTransfer.objects.exists()

        client.force_login(superuser)
        assert client.get(reverse("admin_content_transfer")).status_code == 200

    def test_export_then_download(
        self, client, superuser, project, django_capture_on_commit_callbacks
    ):
        client.force_login(superuser)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(reverse("admin_content_transfer_export"))

        assert response.status_code == 302
        job = ContentTransfer.objects.get()
        assert job.status == ContentTransferStatus.DONE  # eager Celery in tests, once committed
        download = client.get(reverse("admin_content_transfer_download", args=[job.pk]))
        assert download.status_code == 200
        assert download["Content-Disposition"].startswith("attachment")
        assert "no-store" in download["Cache-Control"]
        assert zipfile.ZipFile(io.BytesIO(b"".join(download.streaming_content))).namelist()

    def test_others_cannot_download(self, client, superuser, project):
        job = ContentTransfer.objects.create(kind=ContentTransferKind.EXPORT)
        run_export(job)
        client.force_login(make_user("admin@example.com", role=UserRole.ADMIN))

        assert client.get(
            reverse("admin_content_transfer_download", args=[job.pk])
        ).status_code in (
            302,
            403,
        )

    def test_import_upload(self, client, superuser, project, django_capture_on_commit_callbacks):
        client.force_login(superuser)
        upload = SimpleUploadedFile("content.zip", exported(key=KEY).getvalue())

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(
                reverse("admin_content_transfer"), {"archive": upload, "mode": "create"}
            )

        assert response.status_code == 302
        job = ContentTransfer.objects.get(kind=ContentTransferKind.IMPORT)
        assert (job.mode, job.original_name, job.status) == ("create", "content.zip", "done")
        assert ProjectPage.objects.count() == 2

    def test_wrong_upload_is_refused_at_once(self, client, superuser, project):
        client.force_login(superuser)
        upload = SimpleUploadedFile("content.zip", exported().getvalue())  # unsigned

        response = client.post(
            reverse("admin_content_transfer"), {"archive": upload, "mode": "replace"}
        )

        assert response.status_code == 200
        assert "archive" in response.context["form"].errors
        assert not ContentTransfer.objects.exists()

    def test_import_disabled_in_production(self, client, superuser, settings):
        settings.CONTENT_IMPORT_ENABLED = False
        client.force_login(superuser)

        page = client.get(reverse("admin_content_transfer")).content.decode()
        response = client.post(
            reverse("admin_content_transfer"),
            {"archive": SimpleUploadedFile("c.zip", b"x"), "mode": "replace"},
        )

        assert 'enctype="multipart/form-data"' not in page
        assert response.status_code in (200, 403)
        assert not ContentTransfer.objects.exists()

    def test_menu_entry_for_superusers(self, client, superuser):
        client.force_login(superuser)
        assert (
            reverse("admin_content_transfer")
            in client.get(reverse("wagtailadmin_home")).content.decode()
        )

    def test_archives_are_not_served_as_media(self, client, superuser, project):
        job = ContentTransfer.objects.create(kind=ContentTransferKind.EXPORT)
        run_export(job)

        with patch("django.conf.settings.DEBUG", True):
            response = client.get(f"/media/transfers/{Path(job.archive.name).name}")

        assert response.status_code == 404
