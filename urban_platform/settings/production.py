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

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# TLS is terminated upstream (nginx forwards X-Forwarded-Proto=https). Redirect
# any plaintext request and tell browsers to stick to HTTPS for a year.
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Never send the session or CSRF cookie over plaintext.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Defense-in-depth headers.
SECURE_CONTENT_TYPE_NOSNIFF = True

# Empty env vars must not become a single "" entry, which would be treated as a
# valid host/origin.
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(";") if o]

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(";") if h]
WAGTAILADMIN_BASE_URL = os.environ.get("BASE_URL", "")

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# Cache settings (Redis)
REDIS_URL = os.environ.get("REDIS_URL", "redis://cache:6379/0")

# Separate Redis DB for the content fragment cache: it is flushed wholesale on
# every page publish, so it must not share a DB with sessions (the default).
CONTENT_CACHE_URL = os.environ.get("CONTENT_CACHE_URL") or REDIS_URL.rsplit("/", 1)[0] + "/1"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
    "content": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CONTENT_CACHE_URL,
    },
}

# Session backend using cache
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Celery settings
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

# Use Brevo email service in production
EMAIL_SERVICE_BACKEND = "brevo"
