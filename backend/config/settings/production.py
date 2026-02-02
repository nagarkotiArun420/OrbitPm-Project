from django.core.exceptions import ImproperlyConfigured

from .base import *


DJANGO_ENV = env("DJANGO_ENV", "production")
DEBUG = env_bool("DEBUG", False)
if DEBUG:
    raise ImproperlyConfigured("DEBUG must be disabled in production.")

SECRET_KEY = env("SECRET_KEY", required=True)
if SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("SECRET_KEY must be a strong production secret.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured in production.")

DATABASES = database_config(
    BASE_DIR,
    allow_sqlite_fallback=False,
    require_postgres=True,
    default_conn_max_age=600,
)

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", CORS_ALLOWED_ORIGINS)


# HTTPS and browser security
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env_bool("SECURE_PROXY_SSL_HEADER", False)
    else None
)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", "Lax")
X_FRAME_OPTIONS = "DENY"


# Production static files use hashed filenames after collectstatic.
STORAGES["staticfiles"] = {
    "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
}


# SMTP placeholders are environment-driven for hosted deployments.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "OrbitPM <noreply@example.com>")
SERVER_EMAIL = env("SERVER_EMAIL", DEFAULT_FROM_EMAIL)


# Do not expose the browsable API renderer in production.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
    "common.renderers.StandardJSONRenderer",
)


# Structured logs are friendlier for production ingestion.
LOGGING["handlers"]["console"]["level"] = env("LOG_LEVEL", "INFO")
LOGGING["handlers"]["console"]["formatter"] = env("LOG_FORMATTER", "json")
LOGGING["handlers"]["file"]["formatter"] = env("FILE_LOG_FORMATTER", "json")
LOGGING["handlers"]["error_file"]["formatter"] = env("FILE_LOG_FORMATTER", "json")
