from .base import *
import os
from .base import INSTALLED_APPS as INSTALLED_APPS_BASE

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

INSTALLED_APPS = INSTALLED_APPS_BASE + [
    "django.contrib.postgres",
]

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("DB_NAME"),
    "USER": os.environ.get("DB_USER"),
    "PASSWORD": os.environ.get("DB_PASSWORD"),
    "HOST": os.environ.get("DB_HOST"),
    "PORT": os.environ.get("DB_PORT"),
}

CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
WAGTAILADMIN_BASE_URL = os.environ.get("BASE_URL", "")

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "mediafiles"
