from __future__ import annotations

from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# --- First Party -----------------------------------------------

DEBUG = True
SECRET_KEY = get_random_secret_key()
ROOT_URLCONF = "example_project.config.urls"
WSGI_APPLICATION = "example_project.config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ALLOWED_HOSTS = []

INTERNAL_IPS = [
    "localhost",
    "127.0.0.1",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "debug_toolbar",
    "graphiql_debug_toolbar",
    "graphene_django",
    "example_project.app",
]

MIDDLEWARE = [
    # TODO: Broken, see https://github.com/flavors/django-graphiql-debug-toolbar/pull/27
    # "graphiql_debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "config" / "testdb",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {},
    "formatters": {
        "common": {
            "()": "example_project.config.logging.DotPathFormatter",
            "format": "{asctime} | {levelname} | {module}.{funcName}:{lineno} | {message}",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            "style": "{",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "common",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["stdout"],
    },
}

LANGUAGE_CODE = "en-us"
LANGUAGES = [("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"

# --- Third Party -----------------------------------------------

GRAPHENE = {
    "SCHEMA": "example_project.app.schema.schema",
    "TESTING_ENDPOINT": "/graphql/",
    "MIDDLEWARE": [
        "example_project.config.logging.TracebackMiddleware",
        # "graphene_django.debug.DjangoDebugMiddleware",
    ],
}

GRAPHQL_QUERY_OPTIMIZER = {
    "MAX_COMPLEXITY": 10,
}
