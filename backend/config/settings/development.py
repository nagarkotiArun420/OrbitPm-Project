from .base import *


DJANGO_ENV = env("DJANGO_ENV", "development")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])

DATABASES = database_config(
    BASE_DIR,
    allow_sqlite_fallback=True,
    require_postgres=False,
    default_conn_max_age=0,
)

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", CORS_ALLOWED_ORIGINS)

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

INTERNAL_IPS = env_list("INTERNAL_IPS", ["127.0.0.1"])

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)


# Keep development logging focused on console output.
LOGGING["handlers"]["console"]["level"] = env("LOG_LEVEL", "DEBUG")
for _logger_cfg in LOGGING["loggers"].values():
    _logger_cfg["handlers"] = [
        handler for handler in _logger_cfg.get("handlers", []) if handler == "console"
    ]
LOGGING["handlers"].pop("file", None)
LOGGING["handlers"].pop("error_file", None)
