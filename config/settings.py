from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.core",
    "apps.accounts",
    "apps.posts",
    "apps.utilities",
    "apps.agent",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.LoginRequiredMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.core.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="snp_esb"),
        "USER": env("POSTGRES_USER", default="snp_esb"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="snp_esb"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization -------------------------------------------------

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Yerevan"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("ru", "Русский"),
    ("hy", "Հայերեն"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Static / media --------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static_root"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth -------------------------------------------------------------------

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:landing"
LOGOUT_REDIRECT_URL = "accounts:login"

# Paths reachable without authentication (LoginRequiredMiddleware exemptions).
LOGIN_EXEMPT_PREFIXES = [
    "/robots.txt",
    "/sitemap.xml",
    "/static/",
    "/media/",
    "/admin/",
    "/api/",
]
# Language-prefixed paths are added to the exempt list dynamically for each
# locale in apps.core.middleware, e.g. "/en/accounts/login/".
LOGIN_EXEMPT_URL_NAMES = [
    "accounts:login",
    "accounts:webauthn_login_begin",
    "accounts:webauthn_login_complete",
    "set_language",
]

# --- WebAuthn / PassKey -----------------------------------------------------

WEBAUTHN_RP_ID = env("WEBAUTHN_RP_ID", default="localhost")
WEBAUTHN_RP_NAME = env("WEBAUTHN_RP_NAME", default="SNP ESB")
WEBAUTHN_ORIGIN = env("WEBAUTHN_ORIGIN", default="http://localhost:8000")

# --- ai-assistant (separate service, see /ai-assistant) ----------------------

AI_ASSISTANT_BASE_URL = env("AI_ASSISTANT_BASE_URL", default="http://host.docker.internal:8001")
AI_ASSISTANT_SERVICE_TOKEN = env("AI_ASSISTANT_SERVICE_TOKEN", default="dev-only-shared-token-7f3a9c1e5b8d2f6a")

# --- DRF ---------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# --- Celery ------------------------------------------------------------------

CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# --- Upload limits / conversion rules ----------------------------------------

CONVERSION_MAX_UPLOAD_SIZES = {
    "image": 50 * 1024 * 1024,
    "video": 100 * 1024 * 1024,
    "document": 300 * 1024 * 1024,
}
CONVERSION_FILE_TTL_MINUTES = 30

DATA_UPLOAD_MAX_MEMORY_SIZE = 300 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
