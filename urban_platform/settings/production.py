from .base import *
import os
from .base import INSTALLED_APPS as INSTALLED_APPS_BASE

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

INSTALLED_APPS = INSTALLED_APPS_BASE + [
    "django.contrib.postgres",
]

# statement_timeout (ms) bounds any single query so a runaway/locked query cannot
# hang a worker forever. Applies to every connection using these settings,
# including the migrator and collectstatic — keep it comfortably above the
# slowest expected migration, or set DB_STATEMENT_TIMEOUT_MS=0 to disable.
DB_STATEMENT_TIMEOUT_MS = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "30000"))
_pg_options = (
    "-c statement_timeout=%d" % DB_STATEMENT_TIMEOUT_MS if DB_STATEMENT_TIMEOUT_MS > 0 else ""
)

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("DB_NAME"),
    "USER": os.environ.get("DB_USER"),
    "PASSWORD": os.environ.get("DB_PASSWORD"),
    "HOST": os.environ.get("DB_HOST"),
    "PORT": os.environ.get("DB_PORT"),
    # connect_timeout caps how long a request blocks when Postgres is
    # unreachable but not actively refusing (firewall drop, dead host) — the
    # failure mode that otherwise hangs a worker indefinitely.
    "OPTIONS": {"connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))},
    # Reuse connections across requests instead of reconnecting every time, and
    # health-check a pooled connection before use so a stale one is replaced.
    "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
    "CONN_HEALTH_CHECKS": True,
}
if _pg_options:
    DATABASES["default"]["OPTIONS"]["options"] = _pg_options  # type: ignore[index]

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

# Fail fast when Redis is unreachable or unresponsive. Without these, the
# builtin RedisCache blocks indefinitely — and because sessions live in the
# cache (see SESSION_ENGINE below), every request would hang, taking the whole
# site down. Bounded timeouts turn that into a fast error instead.
REDIS_CACHE_OPTIONS = {
    "socket_connect_timeout": int(os.environ.get("REDIS_CONNECT_TIMEOUT", "2")),
    "socket_timeout": int(os.environ.get("REDIS_SOCKET_TIMEOUT", "2")),
    "retry_on_timeout": True,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": REDIS_CACHE_OPTIONS,
    },
    "content": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CONTENT_CACHE_URL,
        "OPTIONS": REDIS_CACHE_OPTIONS,
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
