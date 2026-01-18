import os
from .base import *

DEBUG = False

# Databases
DB_NAME = os.getenv('DATABASE_NAME')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')
DB_HOST = os.getenv('DATABASE_HOST')
DB_PORT = os.getenv('DATABASE_PORT')

if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]):
    raise ValueError("Production database environment variables are incomplete!")

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

# Security settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static files production storage (Manifest handles cache-busting)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Real SMTP Email backend in production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'

# ---------------------------------------------------------------------------
# Production Logging Overrides
# ---------------------------------------------------------------------------
# Ensure the log directory exists in production.
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Console: INFO level in production (no DEBUG noise).
LOGGING['handlers']['console']['level'] = 'INFO'

# File handlers: use JSON formatter for structured log ingestion.
LOGGING['handlers']['file']['formatter'] = 'json'
LOGGING['handlers']['error_file']['formatter'] = 'json'
