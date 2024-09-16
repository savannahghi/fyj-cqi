import io
import json
import logging

from django.conf import ImproperlyConfigured

import google.auth
import google.auth.exceptions
from google.cloud import secretmanager
from google.oauth2 import service_account

from dotenv import load_dotenv

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *  # noqa
from .base import env


###############################################################################
# READ ENVIRONMENT
###############################################################################

ENV_PATH = env.str("ENV_PATH", default=None)

# First, we try and load the environment variables from an .env file if a path
# to the file is provided.
if ENV_PATH:
    env.read_env(path=ENV_PATH, override=True)
# Else, load the variables from Google Secrets Manager
else:
    SETTINGS_NAME = env.str("SETTINGS_NAME")
    try:
        GCP_PROJECT_ID = env.str(
            "GOOGLE_CLOUD_PROJECT",
            default=google.auth.default()
        )
    except google.auth.exceptions.DefaultCredentialsError:
        raise ImproperlyConfigured(
            "No local .env or GOOGLE_CLOUD_PROJECT detected. No secrets found."
        )

    secret_manager_client = secretmanager.SecretManagerServiceClient()
    secrets_name = "projects/{}/secrets/{}/versions/latest".format(
        GCP_PROJECT_ID, SETTINGS_NAME
    )
    payload = secret_manager_client.access_secret_version(
        name=secrets_name
    ).payload.data.decode("UTF-8")
    load_dotenv(stream=io.StringIO(payload), override=True)


###############################################################################
# LOAD GOOGLE CREDENTIALS
###############################################################################

# Note that when this is not provided and the production environment is Google
# Cloud Run, you will not be able to perform some actions such as signing GCS
# blob URLs.
# See the link below for an example of such an issue:
# https://stackoverflow.com/questions/64234214/how-to-generate-a-blob-signed-url-in-google-cloud-run
GOOGLE_APPLICATION_CREDENTIALS_KEY = env.str(
    "GOOGLE_APPLICATION_CREDENTIALS_KEY",
    default=""
)

if GOOGLE_APPLICATION_CREDENTIALS_KEY:
    GCS_CREDENTIALS = service_account.Credentials.from_service_account_info(
        json.loads(GOOGLE_APPLICATION_CREDENTIALS_KEY)
    )
    # Set variables that define Google Services Credentials
    GS_CREDENTIALS = GCS_CREDENTIALS

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        ".fahariyajamii.org",
        "cqi.fahariyajamii.org",
        ],
    )


###############################################################################
# DJANGO DEV PANEL RECOMMENDATIONS AND OTHER SECURITY
###############################################################################

DEBUG = True

SECRET_KEY = env.str("DJANGO_SECRET_KEY")


###############################################################################
# DATABASE CONFIG
###############################################################################

DATABASES = {
    "default": {
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
        "HOST": env.str("POSTGRES_HOST"),
        "PORT": env.str("POSTGRES_PORT", None),
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": env.int("CONN_MAX_AGE", default=60),
    },
}


###############################################################################
# DATABASE CONFIG
###############################################################################

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}


###############################################################################
# SECURITY
###############################################################################

CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_SECONDS = 518400
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True


###############################################################################
# STORAGES
###############################################################################

INSTALLED_APPS += ["storages"]  # noqa: F405
GS_BUCKET_NAME = env.str("DJANGO_GCP_STORAGE_BUCKET_NAME")
GS_DEFAULT_ACL = "projectPrivate"


#############################################################################
# STATIC ASSETS AND MEDIA FILES
#############################################################################

DEFAULT_FILE_STORAGE = "utils.storages.MediaRootGoogleCloudStorage"
MEDIA_URL = "https://storage.googleapis.com/%s/media/" % GS_BUCKET_NAME
STATICFILES_STORAGE = "utils.storages.StaticRootGoogleCloudStorage"


###############################################################################
# DJANGO COMPRESSOR
###############################################################################

COMPRESS_ENABLED = True
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_URL
COMPRESS_URL = STATIC_URL  # noqa F405
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_OFFLINE
COMPRESS_OFFLINE = (
    True  # Offline compression is required when using Whitenoise
)
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_FILTERS
COMPRESS_FILTERS = {
    "css": [
        "compressor.filters.css_default.CssAbsoluteFilter",
        "compressor.filters.cssmin.rCSSMinFilter",
    ],
    "js": ["compressor.filters.jsmin.JSMinFilter"],
}


###############################################################################
# LOGGING
###############################################################################

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "{levelname}: {asctime} - <module={module} | "
                "function={funcName} | line={lineno:d}> - {message}"
            ),
            "style": "{"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "DEBUG",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        # Errors logged by the SDK itself
        "sentry_sdk": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


###############################################################################
# SENTRY
###############################################################################

SENTRY_DSN = env.str("SENTRY_DSN")
SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

sentry_logging = LoggingIntegration(
    level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
)
integrations = [
    sentry_logging,
    DjangoIntegration(),
]
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=integrations,
    environment=env.str("SENTRY_ENVIRONMENT", default="production"),
    traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=1.0),
)
