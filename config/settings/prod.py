import logging

from .base import *  # noqa
from .base import env
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

###############################################################################
# READ ENVIRONMENT
###############################################################################
ENV_PATH = "/tmp/secrets/.env"
env.read_env(path=ENV_PATH, override=True)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        ".fahariyajamii.org",
        "cqi.fahariyajamii.org",
        ],
    )

SECRET_KEY = env.str("DJANGO_SECRET_KEY")


###############################################################################
# DJANGO DEV PANEL RECOMMENDATIONS AND OTHER SECURITY
###############################################################################

DEBUG = False


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
GS_DEFAULT_ACL = "project-private"


###############################################################################
# STATIC ASSETS AND MEDIA FILES
###############################################################################

DEFAULT_FILE_STORAGE = "utils.storages.MediaRootGoogleCloudStorage"
MEDIA_URL = "https://storage.googleapis.com/%s/media/" % GS_BUCKET_NAME
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"


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
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        # Errors logged by the SDK itself
        "sentry_sdk": {
            "level": "ERROR",
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