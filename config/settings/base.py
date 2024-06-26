"""
Django settings for cqi project.

Generated by 'django-admin startproject' using Django 3.2.5.
"""
import os
from pathlib import Path

import environs

###############################################################################
# READ ENVIRONMENT
###############################################################################
env = environs.Env()

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "fyjcqiprojects.ttl.co.ke", "127.0.0.1", "localhost",
    ],
)
DEBUG = env.bool("DJANGO_DEBUG", False)
DJANGO_LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", default="DEBUG")
SECRET_KEY = env.str("DJANGO_SECRET_KEY", "django-insecure-xlb*ys8xwb04c&=y_z")

###############################################################################
# FILE SYSTEM AND MISC
###############################################################################
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

###############################################################################
# DJANGO DEV PANEL RECOMMENDATIONS AND OTHER SECURITY
###############################################################################

CSRF_USE_SESSIONS = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

###############################################################################
# INSTALLED APPS
###############################################################################

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "compressor",
    "crispy_forms",
    "phonenumber_field",
    "django_filters",
    "multiselectfield",
    "mathfilters",
    "django_select2",
    'django_extensions',
    'ckeditor',
    'ckeditor_uploader',
    # 'debug_toolbar',
    # 'silk',

    # Note: Order of INSTALLED_APPS is important. To ensure that exceptions inside other apps’ signal handlers do not
    # affect the integrity of file deletions within transactions, django_cleanup should be placed last in INSTALLED_APPS
    'django_cleanup.apps.CleanupConfig',
]

LOCAL_APPS = [
    "apps.cqi",
    "apps.account",
    "apps.dqa",
    "apps.pmtct",
    "apps.data_analysis",
    "apps.pharmacy",
    "apps.labpulse",
    "apps.fyj_mentorship",
    "apps.wash_dqa",
    "apps.repo",
    "apps.feedback",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

###############################################################################
# MIDDLEWARE
###############################################################################

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "crum.CurrentRequestUserMiddleware",
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    # "silk.middleware.SilkyMiddleware",
]

###############################################################################
# CORE DJANGO CONFIG
###############################################################################

APPEND_SLASH = True
ASGI_APPLICATION = "config.asgi.application"
BASE_URL = "http://localhost:8000"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
INTERNAL_IPS = ["127.0.0.1"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

###############################################################################
# TEMPLATES
###############################################################################

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["assets/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

###############################################################################
# TRANSLATIONS AND LOCALES
###############################################################################

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
# USE_L10N = True
USE_TZ = True

###############################################################################
# AUTH AND PASSWORDS
###############################################################################

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"  # noqa
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"  # noqa
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"  # noqa
    },
]
AUTH_USER_MODEL = "account.CustomUser"

PASSWORD_HASHERS = [
    # "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

LOGIN_REDIRECT_URL = 'login'
LOGIN_URL = '/accounts/login/'

###############################################################################
# LOGGING
###############################################################################

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(levelname)s %(asctime)s %(module)s "
                "%(process)d %(thread)d %(message)s"
            )
        }
    },
    "handlers": {
        "console": {
            "level": DJANGO_LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

###############################################################################
# OTHER
###############################################################################

ADMIN_URL = "admin/"

###############################################################################
# STATIC ASSETS AND MEDIA FILES
###############################################################################

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "assets" / "static"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
WHITENOISE_MANIFEST_STRICT = False
SESSION_COOKIE_AGE = 14400  # Set the session expiration to 1 hour (in seconds)
###############################
# DEBUG CONFIG
###############################
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}
# SILKY_META = True
# SILKY_PYTHON_PROFILER = True
# SILKY_PYTHON_PROFILER_BINARY = True

CKEDITOR_BASEPATH = "/static/ckeditor/ckeditor/"
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS={
    'default':{
        'toolbar': 'full',
        'removePlugins':'exportpdf',
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = 'FYJ CQI'
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default=None)
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default=None)
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

