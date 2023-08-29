from contextlib import suppress
from pathlib import Path

from django.core.management.utils import get_random_secret_key
from django.utils.log import DEFAULT_LOGGING

BASE_DIR = Path(__file__).resolve().parent.parent

# --- First Party -----------------------------------------------

DEBUG = True
SECRET_KEY = get_random_secret_key()
ROOT_URLCONF = "tests.project.urls"
WSGI_APPLICATION = "tests.project.wsgi.application"
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
    "graphene_django",
    "tests.example",
]

MIDDLEWARE = [
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
        "NAME": BASE_DIR / "project" / "testdb",
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
    "filters": DEFAULT_LOGGING["filters"],
    "formatters": DEFAULT_LOGGING["formatters"],
    "handlers": DEFAULT_LOGGING["handlers"]
    | {
        "default": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": DEFAULT_LOGGING["loggers"],
    "root": {
        "handlers": ["default"],
        "level": "INFO",
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
    "SCHEMA": "tests.example.schema.schema",
    "MIDDLEWARE": [
        "graphene_django.debug.DjangoDebugMiddleware",
    ],
}

with suppress(ImportError):
    import debug_toolbar

    INSTALLED_APPS += [debug_toolbar.__name__]


with suppress(ImportError):
    import graphiql_debug_toolbar

    INSTALLED_APPS += [graphiql_debug_toolbar.__name__]
    MIDDLEWARE.insert(0, "graphiql_debug_toolbar.middleware.DebugToolbarMiddleware")


GRAPHQL_QUERY_OPTIMIZER = {
    "MAX_COMPLEXITY": 10,
}
