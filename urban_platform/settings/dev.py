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

try:
    from .local import *
except ImportError:
    pass
