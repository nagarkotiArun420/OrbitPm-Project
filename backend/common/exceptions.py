"""
Centralized exception handling for OrbitPM.

Provides:
- Custom DRF exception classes for semantically meaningful API errors
- Enhanced global_exception_handler with structured logging
"""

import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

from common.logging import get_correlation_id
from common.responses import error_response


logger = logging.getLogger('common.exceptions')


# ---------------------------------------------------------------------------
# Custom Exception Classes
# ---------------------------------------------------------------------------

class BaseAPIException(APIException):
    """
    Base class for all OrbitPM custom API exceptions.

    Subclasses should set ``status_code``, ``default_detail``, and
    ``default_code`` to provide meaningful defaults.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'A server error occurred.'
    default_code = 'server_error'


class ResourceNotFoundException(BaseAPIException):
    """Raised when a requested resource does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'


class BusinessValidationException(BaseAPIException):
    """
    Raised when a domain / business-rule validation fails.

    Uses HTTP 422 (Unprocessable Entity) to distinguish from DRF's
    built-in 400 serializer validation errors.
    """
    status_code = 422  # HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'The request failed business validation.'
    default_code = 'business_validation_error'


class ServiceUnavailableException(BaseAPIException):
    """Raised when a downstream service or resource is temporarily unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'The service is temporarily unavailable. Please try again later.'
    default_code = 'service_unavailable'


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

def global_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework.
    Standardizes error responses to follow the format:
    {
        "success": False,
        "message": "Error description",
        "data": null,
        "errors": { ...details... },
        "status_code": <int>
    }

    Also logs errors at appropriate severity levels:
    - DEBUG  — 400 validation errors
    - INFO   — 404 not-found
    - WARNING — 401 authentication / 403 permission errors
    - ERROR  — 5xx unexpected server errors
    """
    # Let DRF handle its own recognized exceptions first.
    # This also converts Django's Http404 and PermissionDenied to DRF equivalents.
    response = exception_handler(exc, context)

    # Build a log context dict for every path.
    request = context.get('request')
    log_context = _build_log_context(request, exc)

    if response is not None:
        errors = response.data
        status_code = response.status_code
        message = 'An error occurred while processing your request.'

        if status_code == status.HTTP_400_BAD_REQUEST:
            message = 'Validation failed'
            logger.debug(
                "Validation error at %s: %s",
                log_context.get('path', '?'), errors,
                extra=log_context,
            )
        elif status_code == status.HTTP_401_UNAUTHORIZED:
            message = 'Authentication credentials were not provided or are invalid'
            logger.warning(
                "Authentication failure at %s user=%s",
                log_context.get('path', '?'), log_context.get('user', 'anonymous'),
                extra=log_context,
            )
        elif status_code == status.HTTP_403_FORBIDDEN:
            message = 'You do not have permission to perform this action'
            logger.warning(
                "Permission denied at %s user=%s",
                log_context.get('path', '?'), log_context.get('user', 'anonymous'),
                extra=log_context,
            )
        elif status_code == status.HTTP_404_NOT_FOUND:
            message = 'The requested resource was not found'
            logger.info(
                "Resource not found: %s",
                log_context.get('path', '?'),
                extra=log_context,
            )
        elif status_code == 422:
            message = str(exc.detail) if hasattr(exc, 'detail') else 'Business validation failed'
            logger.info(
                "Business validation error at %s: %s",
                log_context.get('path', '?'), errors,
                extra=log_context,
            )
        else:
            logger.warning(
                "API error %s at %s: %s",
                status_code, log_context.get('path', '?'), errors,
                extra=log_context,
            )

        response.data = error_response(
            errors=errors,
            message=message,
            status_code=status_code,
        ).data
    else:
        # Unhandled system exceptions (e.g. database disconnect, coding error)
        logger.exception(
            "Unhandled exception at %s user=%s: %s",
            log_context.get('path', '?'),
            log_context.get('user', 'anonymous'),
            exc,
            extra=log_context,
        )

        detail = str(exc) if settings.DEBUG else 'A critical server error occurred.'
        response = error_response(
            message='Internal Server Error',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            errors={
                'non_field_errors': [detail]
            },
        )

    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_log_context(request, exc):
    """Build a dict of contextual information for structured logging."""
    context = {
        'correlation_id': get_correlation_id(),
        'exception_type': type(exc).__name__,
    }
    if request is not None:
        context['path'] = getattr(request, 'path', '?')
        context['method'] = getattr(request, 'method', '?')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            context['user'] = str(
                getattr(user, 'email', None)
                or getattr(user, 'username', None)
                or user.pk
            )
        else:
            context['user'] = 'anonymous'
    return context
