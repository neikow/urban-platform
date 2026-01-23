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

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# Cache settings (Redis)
REDIS_URL = os.environ.get("REDIS_URL", "redis://cache:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Session backend using cache
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Celery settings
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
