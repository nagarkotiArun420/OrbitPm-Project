import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def load_environment(base_dir):
    """Load shared and local dotenv files before settings read os.environ."""
    load_dotenv(base_dir / ".env", override=False)
    load_dotenv(base_dir / ".env.local", override=True)


def env(name, default=None, *, required=False):
    value = os.getenv(name)
    if value is None or value == "":
        if required:
            raise ImproperlyConfigured(f"Missing required environment variable: {name}")
        return default
    return value


def env_bool(name, default=False):
    value = env(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False

    raise ImproperlyConfigured(
        f"{name} must be a boolean value: one of {sorted(TRUE_VALUES | FALSE_VALUES)}"
    )


def env_int(name, default=0):
    value = env(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise improperly_configured_int(name) from exc


def improperly_configured_int(name):
    return ImproperlyConfigured(f"{name} must be an integer")


def env_list(name, default=None):
    value = env(name)
    if value is None:
        return list(default or [])

    return [item.strip() for item in value.split(",") if item.strip()]


def env_path(name, default, *, base_dir=None):
    path = Path(env(name, str(default)))
    if base_dir and not path.is_absolute():
        return base_dir / path
    return path


def optional_env(name):
    value = env(name)
    return value if value not in (None, "") else None


def database_config(
    base_dir,
    *,
    allow_sqlite_fallback=True,
    require_postgres=False,
    default_conn_max_age=0,
):
    database_url = env("DATABASE_URL")

    if database_url:
        config = _database_from_url(database_url, require_postgres=require_postgres)
    else:
        config = _database_from_parts()

    if config is None:
        if require_postgres or not allow_sqlite_fallback:
            raise ImproperlyConfigured(
                "Set DATABASE_URL or DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, "
                "DATABASE_HOST, and DATABASE_PORT for PostgreSQL."
            )
        config = _sqlite_database(base_dir)

    _apply_database_runtime_options(config, default_conn_max_age=default_conn_max_age)
    return {"default": config}


def _database_from_parts():
    required = [
        env("DATABASE_NAME"),
        env("DATABASE_USER"),
        env("DATABASE_PASSWORD"),
        env("DATABASE_HOST"),
        env("DATABASE_PORT"),
    ]
    if not all(required):
        return None

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required[0],
        "USER": required[1],
        "PASSWORD": required[2],
        "HOST": required[3],
        "PORT": required[4],
    }


def _database_from_url(database_url, *, require_postgres=False):
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql"}:
        config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
        options = _database_options_from_query(parsed.query)
        if options:
            config["OPTIONS"] = options
        return config

    if scheme == "sqlite" and not require_postgres:
        path = unquote(parsed.path)
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": path if path else ":memory:",
        }

    raise ImproperlyConfigured(
        "DATABASE_URL must use postgres:// or postgresql:// for this environment."
    )


def _database_options_from_query(query):
    raw_options = parse_qs(query, keep_blank_values=False)
    return {key: values[-1] for key, values in raw_options.items() if values}


def _sqlite_database(base_dir):
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": base_dir / "db.sqlite3",
    }


def _apply_database_runtime_options(config, *, default_conn_max_age):
    config["CONN_MAX_AGE"] = env_int("DATABASE_CONN_MAX_AGE", default_conn_max_age)
    config["CONN_HEALTH_CHECKS"] = env_bool("DATABASE_CONN_HEALTH_CHECKS", True)

    if config["ENGINE"] == "django.db.backends.postgresql" and env_bool(
        "DATABASE_SSL_REQUIRE", False
    ):
        config.setdefault("OPTIONS", {})["sslmode"] = "require"
