"""
API request middleware for OrbitPM.

Provides:
- RequestCorrelationMiddleware: assigns a unique correlation ID to every request
- APIRequestLoggingMiddleware: logs structured request/response metadata
"""

import logging
import time

from common.logging import clear_correlation_id, get_correlation_id, set_correlation_id


logger = logging.getLogger('common.middleware')


# ---------------------------------------------------------------------------
# Request Correlation ID Middleware
# ---------------------------------------------------------------------------

class RequestCorrelationMiddleware:
    """
    Assigns a UUID-based correlation ID to every incoming request.

    * Reads ``X-Correlation-ID`` from the request header (to honour
      upstream load-balancers / gateways that already set one).
    * Falls back to generating a new UUID4.
    * Stores the ID in ``request.correlation_id`` and in thread-local
      storage so that :class:`common.logging.CorrelationIdFilter` can
      inject it into every log record.
    * Adds the ``X-Correlation-ID`` response header so that clients and
      upstream services can trace the request end-to-end.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Honour an existing correlation ID from upstream, or generate one.
        incoming_id = request.META.get('HTTP_X_CORRELATION_ID')
        correlation_id = set_correlation_id(incoming_id)
        request.correlation_id = correlation_id

        response = self.get_response(request)

        response['X-Correlation-ID'] = correlation_id

        # Clean up thread-local state after the response is built.
        clear_correlation_id()

        return response


# ---------------------------------------------------------------------------
# API Request Logging Middleware
# ---------------------------------------------------------------------------

# Headers that must never appear in logs.
_SENSITIVE_HEADERS = frozenset({
    'HTTP_AUTHORIZATION',
    'HTTP_COOKIE',
    'HTTP_X_CSRFTOKEN',
})


class APIRequestLoggingMiddleware:
    """
    Logs structured metadata for every API request.

    Logged fields:
        correlation_id, method, path, user, status_code, duration_ms, timestamp

    Only requests whose path starts with ``/api/`` are logged (admin,
    static, and media requests are skipped to keep logs focused).

    Logging levels:
        * **INFO** — 2xx responses (success)
        * **WARNING** — 4xx responses (client error)
        * **ERROR** — 5xx responses (server error)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only log API endpoints.
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        start = time.monotonic()

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        user = self._get_user_display(request)
        correlation_id = getattr(request, 'correlation_id', '-')
        status_code = response.status_code

        log_data = {
            'correlation_id': correlation_id,
            'method': request.method,
            'path': request.path,
            'user': user,
            'status_code': status_code,
            'duration_ms': duration_ms,
        }

        message = (
            f"{request.method} {request.path} "
            f"status={status_code} duration={duration_ms}ms "
            f"user={user} cid={correlation_id}"
        )

        if 200 <= status_code < 300:
            logger.info(message, extra=log_data)
        elif 400 <= status_code < 500:
            logger.warning(message, extra=log_data)
        elif status_code >= 500:
            logger.error(message, extra=log_data)
        else:
            # 3xx redirects — log at debug.
            logger.debug(message, extra=log_data)

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_display(request):
        """Return a human-readable user identifier, or 'anonymous'."""
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return 'anonymous'
        return str(getattr(user, 'email', None) or getattr(user, 'username', None) or user.pk)
