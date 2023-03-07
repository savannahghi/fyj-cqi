from .base import *  # noqa
from .base import env

###############################################################################
# INSTALLED APPS
###############################################################################

INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa

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
    },
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': 'db_cql',
#     }
# }

###############################################################################
# LOGGING
###############################################################################

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "{levelname}: {asctime} - {process:d} {thread:d} - "
                "<module={module} | function={funcName} | line={lineno:d}> - "
                "{message}"
            ),
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "DEBUG",
        },
        "file": {
            "backupCount": 5,
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": "utf-8",
            "filename": BASE_DIR / "logs" / "cqi.log",  # noqa: F405
            "formatter": "verbose",
            "maxBytes": 1048576,  # 1 MB
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": True,
        }
    },
}