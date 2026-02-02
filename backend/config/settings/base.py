from datetime import timedelta
from pathlib import Path

from .env import (
    database_config,
    env,
    env_bool,
    env_int,
    env_list,
    env_path,
    load_environment,
    optional_env,
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_environment(BASE_DIR)

DJANGO_ENV = env("DJANGO_ENV", "development")

SECRET_KEY = env(
    "SECRET_KEY",
    "django-insecure-local-development-orbitpm-change-me",
)
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])

SITE_URL = env("SITE_URL", "http://localhost:8000")
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173")

LOG_DIR = env_path("LOG_DIR", BASE_DIR / "logs", base_dir=BASE_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = env("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third Party Apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    # Local Apps
    "common.apps.CommonConfig",
    "accounts.apps.AccountsConfig",
    "projects.apps.ProjectsConfig",
    "tasks.apps.TasksConfig",
    "teams.apps.TeamsConfig",
    "invoices.apps.InvoicesConfig",
    "notifications.apps.NotificationsConfig",
    "analytics.apps.AnalyticsConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "common.middleware.RequestCorrelationMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.APIRequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database
DATABASES = database_config(BASE_DIR, allow_sqlite_fallback=True, default_conn_max_age=0)


# Password validation
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


# Authentication
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "accounts.backends.CaseInsensitiveModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True


# Static and media files
STATIC_URL = env("STATIC_URL", "/static/")
STATIC_ROOT = env_path("STATIC_ROOT", BASE_DIR / "staticfiles", base_dir=BASE_DIR)

MEDIA_URL = env("MEDIA_URL", "/media/")
MEDIA_ROOT = env_path("MEDIA_ROOT", BASE_DIR / "media", base_dir=BASE_DIR)

FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 2_621_440)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 2_621_440)
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
FILE_UPLOAD_PERMISSIONS = 0o644

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS and CSRF
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [])
CORS_ALLOW_CREDENTIALS = env_bool("CORS_ALLOW_CREDENTIALS", True)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])


# Security
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
SESSION_COOKIE_HTTPONLY = env_bool("SESSION_COOKIE_HTTPONLY", True)
CSRF_COOKIE_HTTPONLY = env_bool("CSRF_COOKIE_HTTPONLY", False)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_CONTENT_TYPE_NOSNIFF = env_bool("SECURE_CONTENT_TYPE_NOSNIFF", True)
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", "same-origin")
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", "DENY")
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", False)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env_bool("SECURE_PROXY_SSL_HEADER", False)
    else None
)


# Email
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = env_int("EMAIL_TIMEOUT", 10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "OrbitPM <noreply@localhost>")
SERVER_EMAIL = env("SERVER_EMAIL", DEFAULT_FROM_EMAIL)


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": env_int("DRF_PAGE_SIZE", 10),
    "EXCEPTION_HANDLER": "common.exceptions.global_exception_handler",
    "DEFAULT_RENDERER_CLASSES": (
        "common.renderers.StandardJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}


# Simple JWT authentication
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env_int("JWT_ACCESS_TOKEN_MINUTES", 15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_TOKEN_DAYS", 7)),
    "ROTATE_REFRESH_TOKENS": env_bool("JWT_ROTATE_REFRESH_TOKENS", True),
    "BLACKLIST_AFTER_ROTATION": env_bool("JWT_BLACKLIST_AFTER_ROTATION", False),
    "UPDATE_LAST_LOGIN": env_bool("JWT_UPDATE_LAST_LOGIN", True),
    "ALGORITHM": env("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": env("JWT_SIGNING_KEY", SECRET_KEY),
    "VERIFYING_KEY": optional_env("JWT_VERIFYING_KEY"),
    "AUDIENCE": optional_env("JWT_AUDIENCE"),
    "ISSUER": optional_env("JWT_ISSUER"),
    "JWK_URL": optional_env("JWT_JWK_URL"),
    "LEEWAY": env_int("JWT_LEEWAY_SECONDS", 0),
    "AUTH_HEADER_TYPES": tuple(env_list("JWT_AUTH_HEADER_TYPES", ["Bearer"])),
    "AUTH_HEADER_NAME": env("JWT_AUTH_HEADER_NAME", "HTTP_AUTHORIZATION"),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": (
        "rest_framework_simplejwt.authentication.default_user_authentication_rule"
    ),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
}


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] [{levelname}] [{name}] [cid:{correlation_id}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": "common.logging.JSONFormatter",
        },
    },
    "filters": {
        "correlation_id": {
            "()": "common.logging.CorrelationIdFilter",
        },
        "sensitive_data": {
            "()": "common.logging.SensitiveDataFilter",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": env("LOG_FORMATTER", "standard"),
            "filters": ["correlation_id", "sensitive_data"],
        },
        "file": {
            "level": env("FILE_LOG_LEVEL", "INFO"),
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "orbitpm.log"),
            "maxBytes": env_int("LOG_MAX_BYTES", 5 * 1024 * 1024),
            "backupCount": env_int("LOG_BACKUP_COUNT", 5),
            "formatter": env("FILE_LOG_FORMATTER", "standard"),
            "filters": ["correlation_id", "sensitive_data"],
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "orbitpm_errors.log"),
            "maxBytes": env_int("LOG_MAX_BYTES", 5 * 1024 * 1024),
            "backupCount": env_int("LOG_BACKUP_COUNT", 5),
            "formatter": env("FILE_LOG_FORMATTER", "standard"),
            "filters": ["correlation_id", "sensitive_data"],
        },
    },
    "loggers": {
        "common": {
            "handlers": ["console", "file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "common.middleware": {
            "handlers": ["console", "file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "common.exceptions": {
            "handlers": ["console", "file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "projects": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "tasks": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
