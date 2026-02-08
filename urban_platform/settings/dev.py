from .base import *
import os
from dotenv import load_dotenv
from .base import INSTALLED_APPS as INSTALLED_APPS_BASE, MIDDLEWARE as MIDDLEWARE_BASE

load_dotenv()

DEBUG = True

INSTALLED_APPS = INSTALLED_APPS_BASE + [
    "django_browser_reload",
]

MIDDLEWARE = MIDDLEWARE_BASE + [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use console email service in development
EMAIL_SERVICE_BACKEND = "console"
