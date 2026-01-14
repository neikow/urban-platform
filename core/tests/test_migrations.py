from django.core.management import call_command
from django.test import TestCase
from io import StringIO


class MigrationTest(TestCase):
    def test_no_pending_migrations(self):
        out = StringIO()
        try:
            call_command("makemigrations", "--check", "--dry-run", stdout=out)
        except SystemExit:
            self.fail(
                "Pending migrations detected. Run 'python manage.py makemigrations'."
            )
        except Exception as e:
            self.fail(f"makemigrations check failed with error: {e}")
