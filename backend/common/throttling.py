"""
API rate-limiting throttle classes for OrbitPM.

Provides reusable, scope-based throttle classes built on DRF's
``SimpleRateThrottle``.  Each class targets a specific abuse vector:

Global defaults (applied via ``DEFAULT_THROTTLE_CLASSES``):
    - AnonBurstThrottle / AnonSustainedThrottle  — unauthenticated users
    - UserBurstThrottle / UserSustainedThrottle  — authenticated users

Per-view overrides:
    - LoginRateThrottle   — tight per-IP limit on authentication endpoints
    - RegisterRateThrottle — limits account-creation attempts
    - WriteOperationThrottle — throttles POST/PUT/PATCH/DELETE only

Rates are configured centrally in ``settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']``.
"""

import logging

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle


logger = logging.getLogger('common.throttling')


# ---------------------------------------------------------------------------
# Global Default Throttles
# ---------------------------------------------------------------------------

class AnonBurstThrottle(AnonRateThrottle):
    """Short-burst rate limit for unauthenticated requests."""

    scope = 'anon_burst'


class AnonSustainedThrottle(AnonRateThrottle):
    """Daily sustained rate limit for unauthenticated requests."""

    scope = 'anon_sustained'


class UserBurstThrottle(UserRateThrottle):
    """Short-burst rate limit for authenticated requests."""

    scope = 'user_burst'


class UserSustainedThrottle(UserRateThrottle):
    """Daily sustained rate limit for authenticated requests."""

    scope = 'user_sustained'


# ---------------------------------------------------------------------------
# Authentication Endpoint Throttles
# ---------------------------------------------------------------------------

class LoginRateThrottle(SimpleRateThrottle):
    """
    Tight per-IP throttle for login (token-obtain) and token-refresh endpoints.

    Always keys on the client IP address regardless of authentication status,
    since login attempts arrive from unauthenticated callers.
    """

    scope = 'login'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

    def throttle_failure(self):
        logger.warning(
            "Login rate limit exceeded — scope=%s",
            self.scope,
        )
        return False


class RegisterRateThrottle(SimpleRateThrottle):
    """
    Per-IP throttle for the registration endpoint.

    Prevents automated mass-account creation from a single source.
    """

    scope = 'register'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

    def throttle_failure(self):
        logger.warning(
            "Registration rate limit exceeded — scope=%s",
            self.scope,
        )
        return False


# ---------------------------------------------------------------------------
# Write-Operation Throttle
# ---------------------------------------------------------------------------

_WRITE_METHODS = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})


class WriteOperationThrottle(SimpleRateThrottle):
    """
    Throttle that only activates on mutating HTTP methods.

    GET, HEAD, and OPTIONS requests pass through without consuming quota.
    Authenticated users are keyed by user ID; anonymous users by IP.
    """

    scope = 'write_ops'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = str(request.user.pk)
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

    def allow_request(self, request, view):
        # Read-only methods are never throttled.
        if request.method not in _WRITE_METHODS:
            return True
        return super().allow_request(request, view)

    def throttle_failure(self):
        logger.warning(
            "Write-operation rate limit exceeded — scope=%s",
            self.scope,
        )
        return False
