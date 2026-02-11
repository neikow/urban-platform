"""
E2E test settings.

Uses a dedicated SQLite database that persists between test runs,
allowing for a real Django server to be used instead of the live_server fixture.
"""

from .base import *  # noqa
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "e2e-test-secret-key-not-for-production")

ALLOWED_HOSTS = ["*"]

# Use a dedicated SQLite database for e2e tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.e2e.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        "LOCATION": "",
    }
}

# Celery settings for e2e testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Use console email service in e2e tests
EMAIL_SERVICE_BACKEND = "console"

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
