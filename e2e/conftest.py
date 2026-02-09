import os
from dataclasses import dataclass

import pytest
from core.models import User

from wagtail.models import Site, Page, Locale
from home.models import HomePage
from legal.models import (
    CodeOfConductPage,
    TermsOfServicePage,
    PrivacyPolicyPage,
    CookiesPolicyPage,
    LegalIndexPage,
)
from pedagogy.models import PedagogyIndexPage
from publications.models import PublicationIndexPage


def pytest_configure(config: pytest.Config) -> None:
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture(scope="function")
def wagtail_locale():
    locale, _ = Locale.objects.get_or_create(language_code="fr", defaults={"language_code": "fr"})
    yield locale


@pytest.fixture(scope="function")
def setup_wagtail_pages(wagtail_locale):
    root = Page.get_first_root_node()
    if not root:
        root = Page.add_root(title="Root", locale=wagtail_locale)

    home = HomePage.objects.first()
    if not home:
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)

    home.save_revision().publish()

    Site.objects.get_or_create(
        hostname="localhost", defaults={"root_page": home, "is_default_site": True}
    )

    if not PublicationIndexPage.objects.live().exists():
        publication_index = PublicationIndexPage(
            title="Publications",
            slug="publications",
            show_in_menus=True,
            page_introduction="Découvrez les projets et événements en cours et à venir dans votre quartier.",
        )
        home.add_child(instance=publication_index)
        publication_index.save_revision().publish()

    if not PedagogyIndexPage.objects.live().exists():
        pedagogy_index = PedagogyIndexPage(
            title="Fiches pédagogiques",
            slug="fiches-pedagogiques",
            show_in_menus=True,
            page_introduction="Découvrez les fiches pédagogiques",
        )
        home.add_child(instance=pedagogy_index)
        pedagogy_index.save_revision().publish()


def create_legal_page(
    legal_index: LegalIndexPage,
    page_class: type[Page],
    title: str,
    slug: str,
    filename: str,
    locale: Locale,
):
    base_dir = os.path.join("legal", "templates", "legal", "placeholders")
    file_path = os.path.join(base_dir, filename)

    if not os.path.exists(file_path):
        raise RuntimeError(f"Placeholder file not found: {file_path}")

    page = page_class.objects.live().first()
    if page:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                new_html = f.read()
            page.content = new_html
            page.save_revision().publish()
        except IOError as e:
            raise RuntimeError(f"Failed to read placeholder file {file_path}: {e}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        raise RuntimeError(f"Failed to read placeholder file {file_path}: {e}")

    page = page_class(
        title=title,
        slug=slug,
        locale=locale,
        content=content,
    )
    legal_index.add_child(instance=page)
    page.save_revision().publish()


@dataclass
class LegalPageDefinition:
    page_class: type[Page]
    title: str
    slug: str
    filename: str


@pytest.fixture(scope="function")
def setup_legal_pages(wagtail_locale, setup_wagtail_pages):
    legal_index = LegalIndexPage.objects.live().first()
    if not legal_index:
        home = HomePage.objects.first()
        if not home:
            raise RuntimeError("HomePage not found. Ensure it exists before running tests.")

        legal_index = LegalIndexPage(
            title="Legal",
            slug="legal",
            locale=wagtail_locale,
        )
        home.add_child(instance=legal_index)
        legal_index.save_revision().publish()

    if not legal_index.live:
        legal_index.save_revision().publish()

    legal_definitions = [
        LegalPageDefinition(
            page_class=CodeOfConductPage,
            filename="code_of_conduct.html",
            slug="charte",
            title="Charte de conduite",
        ),
        LegalPageDefinition(
            page_class=TermsOfServicePage,
            filename="terms_of_service.html",
            slug="termes",
            title="Termes de conduite",
        ),
        LegalPageDefinition(
            page_class=CookiesPolicyPage,
            filename="cookies_policy.html",
            slug="cookies",
            title="Politique de cookies",
        ),
        LegalPageDefinition(
            page_class=PrivacyPolicyPage,
            filename="privacy_policy.html",
            slug="confidentialite",
            title="Politique de confidentialité",
        ),
    ]

    for definition in legal_definitions:
        create_legal_page(
            legal_index=legal_index,
            page_class=definition.page_class,
            filename=definition.filename,
            slug=definition.slug,
            title=definition.title,
            locale=wagtail_locale,
        )


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Automatically enable database access for all tests."""
    pass


@pytest.fixture
def email():
    yield "e2e.user@email.com"


@pytest.fixture
def password():
    yield "password123"


@pytest.fixture
def e2e_default_user(db, email, password):
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name="E2E",
        last_name="Test",
        postal_code="13007",
    )
    yield user


@pytest.fixture
def e2e_wagtail_admin_user(db, email, password):
    from django.contrib.auth.models import Group, Permission
    from wagtail.models import Page

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name="E2E",
        last_name="WagtailAdmin",
        postal_code="13007",
        is_staff=True,
    )

    # Get or create the Editors group
    editors_group, _ = Group.objects.get_or_create(name="Editors")

    # Add Wagtail admin access permission
    wagtail_admin_permission = Permission.objects.get(codename="access_admin")
    editors_group.permissions.add(wagtail_admin_permission)

    # Grant page permissions to the group on the root page
    Page.get_first_root_node()
    # Add user to the Editors group
    user.groups.add(editors_group)

    user.save()

    yield user


@pytest.fixture
def e2e_superadmin_user(db, email, password):
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name="E2E",
        last_name="Admin",
        postal_code="13007",
    )
    yield user


@pytest.fixture
def live_server(live_server, settings):
    settings.STATIC_URL = live_server.url + "/static/"
    settings.DEBUG = True

    yield live_server
