import os
from .base import *

DEBUG = True

# Database Configuration (PostgreSQL with SQLite fallback for ease of initial development setup)
DB_NAME = os.getenv('DATABASE_NAME')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')
DB_HOST = os.getenv('DATABASE_HOST')
DB_PORT = os.getenv('DATABASE_PORT')

if all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }
else:
    # Fallback to local SQLite for smooth setup and execution when PostgreSQL is not configured yet
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Email Backend - Console for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ---------------------------------------------------------------------------
# Development Logging Overrides
# ---------------------------------------------------------------------------
# In development we only log to the console at DEBUG level.
# File handlers are disabled to avoid cluttering the local filesystem.
LOGGING['handlers']['console']['level'] = 'DEBUG'

# Disable file handlers in development (remove them from all loggers).
for _logger_cfg in LOGGING['loggers'].values():
    _logger_cfg['handlers'] = [
        h for h in _logger_cfg.get('handlers', []) if h == 'console'
    ]
