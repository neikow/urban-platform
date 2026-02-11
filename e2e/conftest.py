import logging
import os
from dataclasses import dataclass
from typing import Any, Generator

import pytest
from django.conf import LazySettings
from pytest_django.live_server_helper import LiveServer
from wagtail.images.models import Image

from core.models import User

from wagtail.models import Site, Page, Locale, Collection

from core.tests.utils.factories import ImageFactory
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

logger = logging.getLogger(__name__)


def pytest_configure(config: pytest.Config) -> None:
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture(scope="function")
def wagtail_locale() -> Generator[Locale, Any, None]:
    locale, _ = Locale.objects.get_or_create(language_code="fr", defaults={"language_code": "fr"})
    yield locale


@pytest.fixture(scope="function")
def wagtail_root(wagtail_locale: Locale) -> Generator[Page, Any, None]:
    root = Page.add_root(title="Root", locale=wagtail_locale)

    yield root

    root.delete()


@pytest.fixture(scope="function")
def home_page(wagtail_locale: Locale, wagtail_root: Page) -> Generator[HomePage, Any, None]:
    home = HomePage.objects.first()
    if not home:
        home = HomePage(title="Home", slug="home")
        wagtail_root.add_child(instance=home)

    home.save_revision().publish()

    site, _ = Site.objects.get_or_create(
        hostname="localhost", defaults={"root_page": home, "is_default_site": True}
    )

    yield home

    site.delete()
    home.delete()


@pytest.fixture(scope="function")
def setup_wagtail_pages(wagtail_locale: Locale, home_page: HomePage) -> Generator[None, None, None]:
    if not (publication_index := PublicationIndexPage.objects.first()):
        publication_index = PublicationIndexPage(
            title="Publications",
            slug="publications",
            show_in_menus=True,
            page_introduction="Découvrez les projets et événements en cours et à venir dans votre quartier.",
        )
        home_page.add_child(instance=publication_index)
    publication_index.save_revision().publish()

    if not (pedagogy_index := PedagogyIndexPage.objects.first()):
        pedagogy_index = PedagogyIndexPage(
            title="Fiches pédagogiques",
            slug="fiches-pedagogiques",
            show_in_menus=True,
            page_introduction="Découvrez les fiches pédagogiques",
        )
        home_page.add_child(instance=pedagogy_index)
    pedagogy_index.save_revision().publish()

    yield None

    pedagogy_index.delete()
    publication_index.delete()


def create_legal_page(
    legal_index: LegalIndexPage,
    page_class: type[Page],
    title: str,
    slug: str,
    filename: str,
    locale: Locale,
) -> None:
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
def setup_legal_pages(
    wagtail_locale: Locale, home_page: HomePage, setup_wagtail_pages: None
) -> Generator[None, None, None]:
    legal_index = LegalIndexPage.objects.live().first()
    if not legal_index:
        legal_index = LegalIndexPage(
            title="Legal",
            slug="legal",
            locale=wagtail_locale,
        )
        home_page.add_child(instance=legal_index)
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

    yield None

    for definition in legal_definitions:
        page = definition.page_class.objects.live().first()
        if page:
            page.delete()

    legal_index.delete()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db: Any) -> None:
    """Automatically enable database access for all tests."""
    pass


@pytest.fixture
def email() -> Generator[str, None, None]:
    yield "e2e.user@email.com"


@pytest.fixture
def password() -> Generator[str, None, None]:
    yield "password123"


@pytest.fixture
def e2e_default_user(db: Any, email: str, password: str) -> Generator[User, None, None]:
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name="E2E",
        last_name="Test",
        postal_code="13007",
    )
    yield user

    user.delete()


@pytest.fixture
def e2e_wagtail_admin_user(
    db: Any, home_page: HomePage, email: str, password: str
) -> Generator[User, None, None]:
    from django.contrib.auth.models import Group, Permission

    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name="E2E",
        last_name="WagtailAdmin",
        postal_code="13007",
        is_staff=True,
    )

    editors_group, _ = Group.objects.get_or_create(name="Moderator")

    wagtail_admin_permission = Permission.objects.get(codename="access_admin")
    editors_group.permissions.add(wagtail_admin_permission)

    editors_group.permissions.add(Permission.objects.get(codename="add_page"))
    editors_group.permissions.add(Permission.objects.get(codename="change_page"))
    editors_group.permissions.add(Permission.objects.get(codename="delete_page"))
    editors_group.permissions.add(Permission.objects.get(codename="publish_page"))
    editors_group.permissions.add(Permission.objects.get(codename="unlock_page"))
    editors_group.permissions.add(Permission.objects.get(codename="add_revision"))

    user.groups.add(editors_group)

    user.save()

    yield user

    user.delete()


@pytest.fixture
def e2e_superadmin_user(email: str, password: str) -> Generator[User, None, None]:
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name="E2E",
        last_name="Admin",
        postal_code="13007",
    )

    yield user

    user.delete()


@pytest.fixture
def mock_image() -> Generator[Image, None, None]:
    if collection := Collection.get_first_root_node() is None:
        collection = Collection.add_root(
            name="Root Collection",
        )

    yield ImageFactory.create(
        collection=collection,
    )


@pytest.fixture
def live_server(
    live_server: LiveServer, settings: LazySettings
) -> Generator[LiveServer, None, None]:
    settings.STATIC_URL = live_server.url + "/static/"
    settings.DEBUG = True

    yield live_server
