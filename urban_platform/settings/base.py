import os
from pathlib import Path

import django_stubs_ext
from celery.schedules import crontab
from dotenv import load_dotenv

from urban_platform.tools.setup_sentry import setup_sentry

load_dotenv()

# Models annotate fields as generics (models.CharField[str, str]); Django's
# field classes only accept subscripting once django-stubs-ext patches them.
# This used to happen implicitly when Wagtail pulled in django-tasks.
django_stubs_ext.monkeypatch()

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent

# Default name, until one is set in the admin (Settings › Branding).
WEBSITE_NAME = os.environ.get("WEBSITE_NAME", "Urbix")

ANALYTICS_SCRIPT_TAG = os.environ.get("ANALYTICS_SCRIPT_TAG", "")

# Application definition

INSTALLED_APPS = [
    "core",
    "home",
    "about",
    "legal",
    "pedagogy",
    "publications",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.routable_page",
    "wagtail.contrib.settings",
    "wagtail.embeds",
    "wagtail.sites",
    "core.apps.CustomUsersAppConfig",  # replaces "wagtail.users" to add role management
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.locales",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "django_celery_beat",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "urban_platform.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            PROJECT_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.project_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "urban_platform.wsgi.application"

# Authentication
AUTH_USER_MODEL = "core.User"

# Point Django auth (e.g. LoginRequiredMixin) at the platform's own login route
# instead of the framework default /accounts/login/, which does not exist here
# and would 404 unauthenticated users (e.g. after email verification).
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "me"

# Grants Wagtail admin access (wagtailadmin.access_admin) based on user role,
# replacing the deprecated is_staff flag. See core.auth_backends.
AUTHENTICATION_BACKENDS = [
    "core.auth_backends.RolePermissionsBackend",
]


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "fr"
LANGUAGES = [
    ("fr", "Français"),
]

TIME_ZONE = "Europe/Paris"

USE_I18N = True
WAGTAIL_I18N_ENABLED = False

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [
    PROJECT_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Default storage settings
# See https://docs.djangoproject.com/en/6.0/ref/settings/#std-setting-STORAGES
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Django sets a maximum of 1000 fields per form by default, but particularly complex page models
# can exceed this limit within Wagtail's page editor.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000


# Wagtail settings

WAGTAIL_SITE_NAME = WEBSITE_NAME
LOCALE_PATHS = [
    PROJECT_DIR / "locale",
]

# Search
# https://docs.wagtail.org/en/stable/topics/search/backends.html
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
WAGTAILADMIN_BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Disable Wagtail's default password reset functionality
WAGTAIL_PASSWORD_RESET_ENABLED = False
# Allowed file extensions for documents in the document library.
# This can be omitted to allow all files, but note that this may present a security risk
# if untrusted users are allowed to upload files -
# see https://docs.wagtail.org/en/stable/advanced_topics/deploying.html#user-uploaded-files
WAGTAILDOCS_EXTENSIONS = [
    "csv",
    "docx",
    "key",
    "odt",
    "pdf",
    "pptx",
    "rtf",
    "txt",
    "xlsx",
    "zip",
]

setup_sentry(
    dsn=os.environ.get("SENTRY_DSN", ""),
    environment=os.environ.get("ENVIRONMENT", "dev"),
)

EMAIL_VERIFICATION_TOKEN_EXPIRY = 86400
PASSWORD_RESET_TOKEN_EXPIRY = 3600
EMAIL_EVENT_ANONYMIZE_DAYS = 30

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
# Moderation workflow emails (submitted, approved, rejected pages), in HTML.
WAGTAILADMIN_NOTIFICATION_USE_HTML = True
# Empty: the website name of the Branding setting (core.branding.sender_name).
DEFAULT_FROM_NAME = os.environ.get("DEFAULT_FROM_NAME", "")

# Task modules outside "<app>.tasks", which autodiscovery would miss.
CELERY_IMPORTS = ("core.emails.tasks", "core.notifications.tasks")
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    "send-event-reminders": {
        "task": "publications.tasks.send_event_reminders",
        # The day before, at 9:00 Paris time (CELERY_TIMEZONE).
        "schedule": crontab(hour="9", minute="0"),
    },
    "close-expired-polls": {
        "task": "publications.tasks.close_expired_polls",
        "schedule": 15 * 60,
    },
    "refresh-map-tiles": {
        "task": "publications.tasks.refresh_map_tiles",
        # Daily check; the task only downloads once the interval set in the
        # admin (Settings › Map) has passed.
        "schedule": crontab(hour="4", minute="30"),
    },
    "prune-security-events": {
        "task": "core.tasks.prune_security_events",
        "schedule": crontab(hour="3", minute="20"),
    },
    "prune-task-runs": {
        "task": "core.tasks.prune_task_runs",
        "schedule": crontab(hour="3", minute="15"),
    },
    "anonymize-old-email-events": {
        "task": "core.emails.tasks.anonymize_old_email_events",
        "schedule": 86400,
    },
}
