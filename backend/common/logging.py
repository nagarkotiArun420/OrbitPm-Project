"""
Reusable logging utilities for OrbitPM.

Provides:
- Thread-local correlation ID management
- CorrelationIdFilter: injects correlation_id into every log record
- SensitiveDataFilter: redacts sensitive fields from log output
- JSONFormatter: structured JSON log formatter for production
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Thread-local correlation ID storage
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def get_correlation_id():
    """Return the correlation ID for the current request thread, or '-'."""
    return getattr(_thread_local, 'correlation_id', '-')


def set_correlation_id(correlation_id=None):
    """
    Set the correlation ID for the current request thread.

    If *correlation_id* is ``None`` a new UUID4 is generated.
    """
    _thread_local.correlation_id = correlation_id or str(uuid.uuid4())
    return _thread_local.correlation_id


def clear_correlation_id():
    """Remove the correlation ID after the request is finished."""
    _thread_local.correlation_id = '-'


# ---------------------------------------------------------------------------
# Logging Filters
# ---------------------------------------------------------------------------

class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds ``correlation_id`` to every log record.

    Attach this filter to handlers or loggers so that formatters can
    reference ``%(correlation_id)s``.
    """

    def filter(self, record):
        record.correlation_id = get_correlation_id()
        return True


# Fields whose values should never appear in logs.
_SENSITIVE_KEYS = frozenset({
    'password', 'token', 'secret', 'access_token', 'refresh_token',
    'authorization', 'cookie', 'api_key', 'credit_card',
})


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that redacts values of known-sensitive keys in the
    log record's message and args.

    This is a best-effort safeguard — it scans ``record.msg`` for
    occurrences of sensitive key names and replaces adjacent quoted
    values with ``[REDACTED]``.
    """

    def filter(self, record):
        if isinstance(record.msg, dict):
            record.msg = self._redact_dict(record.msg)
        elif isinstance(record.msg, str):
            for key in _SENSITIVE_KEYS:
                if key in record.msg.lower():
                    record.msg = self._redact_string(record.msg, key)
        return True

    @staticmethod
    def _redact_dict(data):
        """Return a shallow copy with sensitive values replaced."""
        cleaned = {}
        for key, value in data.items():
            if key.lower() in _SENSITIVE_KEYS:
                cleaned[key] = '[REDACTED]'
            elif isinstance(value, dict):
                cleaned[key] = SensitiveDataFilter._redact_dict(value)
            else:
                cleaned[key] = value
        return cleaned

    @staticmethod
    def _redact_string(msg, key):
        """Best-effort inline redaction of 'key=...' or 'key: ...' patterns."""
        import re
        # Matches key=value or key: value patterns (quoted or unquoted)
        pattern = re.compile(
            rf"({re.escape(key)})\s*[=:]\s*['\"]?[^'\",\s]+['\"]?",
            re.IGNORECASE,
        )
        return pattern.sub(rf"\1=[REDACTED]", msg)


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """
    Outputs each log record as a single-line JSON object.

    Suitable for production environments where logs are ingested by
    structured-logging platforms (ELK, Datadog, CloudWatch, etc.).
    """

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'correlation_id': getattr(record, 'correlation_id', '-'),
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)
