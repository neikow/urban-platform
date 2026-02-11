#!/usr/bin/env python

import argparse
import os
import subprocess  # nosec
import sys
from pathlib import Path
from typing import TypedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
E2E_DB_PATH = PROJECT_ROOT / "db.e2e.sqlite3"
E2E_SETTINGS_MODULE = "urban_platform.settings.e2e"
E2E_SERVER_HOST = "127.0.0.1"
E2E_SERVER_PORT = 8001


def setup_django() -> None:
    """Set up Django environment."""
    # Add project root to path so Django can find the settings module
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.environ["DJANGO_SETTINGS_MODULE"] = E2E_SETTINGS_MODULE
    import django

    django.setup()


def run_migrations() -> None:
    """Run database migrations for the E2E database."""
    print("🔄 Running migrations...")
    result = subprocess.run(  # nosec
        [
            sys.executable,
            "manage.py",
            "migrate",
            "--settings",
            E2E_SETTINGS_MODULE,
        ],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print("❌ Migrations failed")
        sys.exit(1)
    print("✅ Migrations completed")


def collect_static() -> None:
    """Collect static files."""
    print("📦 Collecting static files...")
    result = subprocess.run(  # nosec
        [
            sys.executable,
            "manage.py",
            "collectstatic",
            "--noinput",
            "--settings",
            E2E_SETTINGS_MODULE,
        ],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print("❌ Static file collection failed")
        sys.exit(1)
    print("✅ Static files collected")


def populate_database() -> None:
    """Populate the E2E database with required test data."""
    setup_django()

    from django.contrib.auth.models import Group, Permission
    from wagtail.models import Site, Page, Locale, Collection

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

    print("🌱 Populating E2E database...")

    locale, _ = Locale.objects.get_or_create(language_code="fr", defaults={"language_code": "fr"})
    print(f"  ✓ Locale: {locale.language_code}")

    root = Page.objects.filter(depth=1).first()
    if not root:
        root = Page.add_root(title="Root", locale=locale)
        print("  ✓ Created root page")
    else:
        print("  ✓ Root page exists")

    home = HomePage.objects.first()
    if not home:
        home = HomePage(title="Accueil", slug="home", locale=locale)
        root.add_child(instance=home)
        home.save_revision().publish()
        print("  ✓ Created home page")
    else:
        if not home.live:
            home.save_revision().publish()
        print("  ✓ Home page exists")

    site, created = Site.objects.get_or_create(
        hostname="localhost",
        defaults={"root_page": home, "is_default_site": True, "port": E2E_SERVER_PORT},
    )
    if not created:
        site.root_page = home
        site.is_default_site = True
        site.port = E2E_SERVER_PORT
        site.save()
    print(f"  ✓ Site configured for localhost:{E2E_SERVER_PORT}")

    if not PublicationIndexPage.objects.exists():
        publication_index = PublicationIndexPage(
            title="Publications",
            slug="publications",
            show_in_menus=True,
            page_introduction="Découvrez les projets et événements en cours et à venir dans votre quartier.",
            locale=locale,
        )
        home.add_child(instance=publication_index)
        publication_index.save_revision().publish()
        print("  ✓ Created publication index")
    else:
        print("  ✓ Publication index exists")

    if not PedagogyIndexPage.objects.exists():
        pedagogy_index = PedagogyIndexPage(
            title="Fiches pédagogiques",
            slug="fiches-pedagogiques",
            show_in_menus=True,
            page_introduction="Découvrez les fiches pédagogiques",
            locale=locale,
        )
        home.add_child(instance=pedagogy_index)
        pedagogy_index.save_revision().publish()
        print("  ✓ Created pedagogy index")
    else:
        print("  ✓ Pedagogy index exists")

    legal_index = LegalIndexPage.objects.first()
    if not legal_index:
        legal_index = LegalIndexPage(
            title="Mentions légales",
            slug="legal",
            locale=locale,
        )
        home.add_child(instance=legal_index)
        legal_index.save_revision().publish()
        print("  ✓ Created legal index")
    else:
        if not legal_index.live:
            legal_index.save_revision().publish()
        print("  ✓ Legal index exists")

    class LegalPageDefinition(TypedDict):
        model: type[Page]
        title: str
        slug: str
        filename: str

    legal_pages: list[LegalPageDefinition] = [
        {
            "model": CodeOfConductPage,
            "title": "Charte de conduite",
            "slug": "charte",
            "filename": "code_of_conduct.html",
        },
        {
            "model": TermsOfServicePage,
            "title": "Termes de service",
            "slug": "termes",
            "filename": "terms_of_service.html",
        },
        {
            "model": CookiesPolicyPage,
            "title": "Politique de cookies",
            "slug": "cookies",
            "filename": "cookies_policy.html",
        },
        {
            "model": PrivacyPolicyPage,
            "title": "Politique de confidentialité",
            "slug": "confidentialite",
            "filename": "privacy_policy.html",
        },
    ]

    for page_def in legal_pages:
        model = page_def["model"]
        if not (page := model.objects.first()):
            # Read content from placeholder file
            placeholder_path = (
                PROJECT_ROOT
                / "legal"
                / "templates"
                / "legal"
                / "placeholders"
                / page_def["filename"]
            )
            content = ""
            if placeholder_path.exists():
                content = placeholder_path.read_text(encoding="utf-8")

            page = model(
                title=page_def["title"],
                slug=page_def["slug"],
                locale=locale,
                content=content,
            )
            legal_index.add_child(instance=page)
            page.save_revision().publish()
            print(f"  ✓ Created {page_def['title']}")
        else:
            page.save_revision().publish()
            print(f"  ✓ {page_def['title']} exists")

    # Create root collection if needed
    if not Collection.objects.filter(depth=1).exists():
        Collection.add_root(name="Root")
        print("  ✓ Created root collection")

    # Create images
    from core.tests.utils.factories import ImageFactory

    ImageFactory.create_batch(10, collection=Collection.objects.first())
    print("  ✓ Created test images")

    # Create moderator group with permissions
    editors_group, created = Group.objects.get_or_create(name="Moderator")
    if created:
        wagtail_admin_permission = Permission.objects.get(codename="access_admin")
        editors_group.permissions.add(wagtail_admin_permission)
        editors_group.permissions.add(Permission.objects.get(codename="add_page"))
        editors_group.permissions.add(Permission.objects.get(codename="change_page"))
        editors_group.permissions.add(Permission.objects.get(codename="delete_page"))
        editors_group.permissions.add(Permission.objects.get(codename="publish_page"))
        editors_group.permissions.add(Permission.objects.get(codename="unlock_page"))
        editors_group.permissions.add(Permission.objects.get(codename="add_revision"))
        print("  ✓ Created Moderator group")
    else:
        print("  ✓ Moderator group exists")

    print("✅ Database population completed!")


def create_test_users() -> None:
    """Create default test users for E2E testing."""
    setup_django()

    from django.contrib.auth.models import Group
    from core.models import User

    print("👤 Creating test users...")

    # Regular test user
    email = "e2e.user@email.com"
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(
            email=email,
            password="password123",  # nosec
            first_name="E2E",
            last_name="Test",
            postal_code="13007",
        )
        print(f"  ✓ Created regular user: {email}")
    else:
        print(f"  ✓ Regular user exists: {email}")

    # Admin test user
    admin_email = "e2e.admin@email.com"
    if not User.objects.filter(email=admin_email).exists():
        admin_user = User.objects.create_superuser(
            email=admin_email,
            password="password123",  # nosec
            first_name="E2E",
            last_name="Admin",
            postal_code="13007",
            is_staff=True,
        )
        editors_group = Group.objects.get(name="Moderator")
        admin_user.groups.add(editors_group)
        admin_user.save()
        print(f"  ✓ Created admin user: {admin_email}")
    else:
        print(f"  ✓ Admin user exists: {admin_email}")

    print("✅ Test users ready!")


def reset_database() -> None:
    """Reset the E2E database by deleting it and running migrations."""
    print("🗑️  Resetting E2E database...")

    if E2E_DB_PATH.exists():
        E2E_DB_PATH.unlink()
        print(f"  ✓ Deleted {E2E_DB_PATH.name}")

    run_migrations()
    populate_database()
    create_test_users()

    print("✅ Database reset completed!")


def start_server(foreground: bool = True) -> subprocess.Popen | None:
    """Start the Django development server for E2E testing."""
    print(f"🚀 Starting E2E server on {E2E_SERVER_HOST}:{E2E_SERVER_PORT}...")

    cmd = [
        sys.executable,
        "manage.py",
        "runserver",
        f"{E2E_SERVER_HOST}:{E2E_SERVER_PORT}",
        "--settings",
        E2E_SETTINGS_MODULE,
        "--noreload",
    ]

    if foreground:
        try:
            subprocess.run(cmd, cwd=PROJECT_ROOT)  # nosec
        except KeyboardInterrupt:
            print("\n👋 Server stopped")
        return None
    else:
        process = subprocess.Popen(  # nosec
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"  ✓ Server started (PID: {process.pid})")
        return process


def run_tests(
    test_path: str | None = None, headed: bool = False, generate_artifacts: bool = False
) -> int:
    """Run E2E tests using pytest."""
    print("🧪 Running E2E tests...")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_path or "e2e/",
        "-v",
    ]

    if generate_artifacts:
        cmd.extend(
            [
                "--screenshot=only-on-failure",
                "--video=retain-on-failure",
                "--trace=retain-on-failure",
                "--output=test-results",
            ]
        )

    if headed:
        cmd.extend(["--headed"])

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)  # nosec
    return result.returncode


def setup(skip_static: bool = False) -> None:
    """Full setup: migrations, static files, database population, and test users."""
    print("🔧 Setting up E2E environment...")

    if not E2E_DB_PATH.exists():
        run_migrations()
    else:
        print("✓ Database exists, running migrations to ensure it's up to date...")
        run_migrations()

    if not skip_static:
        collect_static()

    populate_database()
    create_test_users()

    print("\n✅ E2E environment is ready!")
    print(f"   Database: {E2E_DB_PATH}")
    print(f"   Server will run on: http://{E2E_SERVER_HOST}:{E2E_SERVER_PORT}")
    print("\n   To start the server: python scripts/e2e.py serve")
    print("   To run tests: python scripts/e2e.py test")


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E Test Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    setup_parser = subparsers.add_parser("setup", help="Set up E2E environment")
    setup_parser.add_argument(
        "--skip-static",
        action="store_true",
        help="Skip collecting static files",
    )

    subparsers.add_parser("serve", help="Start the E2E test server")

    subparsers.add_parser("populate", help="Populate the E2E database")

    subparsers.add_parser("reset", help="Reset the E2E database")

    test_parser = subparsers.add_parser("test", help="Run E2E tests")
    test_parser.add_argument(
        "test_path",
        nargs="?",
        help="Specific test file or directory to run",
    )
    test_parser.add_argument(
        "--headed",
        action="store_true",
        help="Run tests in headed mode (show browser)",
    )

    subparsers.add_parser("migrate", help="Run migrations for E2E database")

    subparsers.add_parser("ci", help="Run full E2E setup and tests for CI environments")

    args = parser.parse_args()

    if args.command == "setup":
        setup(skip_static=args.skip_static)
    elif args.command == "serve":
        start_server()
    elif args.command == "populate":
        populate_database()
        create_test_users()
    elif args.command == "reset":
        reset_database()
    elif args.command == "test":
        sys.exit(run_tests(args.test_path, args.headed))
    elif args.command == "migrate":
        run_migrations()
    elif args.command == "ci":
        reset_database()
        start_server(foreground=False)
        sys.exit(
            run_tests(
                headed=False,
                generate_artifacts=True,
            )
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
