from rest_framework.response import Response
from rest_framework import status


DEFAULT_SUCCESS_MESSAGE = 'Operation completed successfully'
DEFAULT_ERROR_MESSAGE = 'Request could not be processed'


def build_response_payload(success, message, data=None, errors=None):
    """
    Builds the standard OrbitPM API response envelope.
    """
    return {
        'success': success,
        'message': message,
        'data': data,
        'errors': errors,
    }


def success_response(data=None, message=DEFAULT_SUCCESS_MESSAGE, status_code=status.HTTP_200_OK):
    """
    Returns a DRF Response using the standard success envelope.
    """
    return Response(
        build_response_payload(
            success=True,
            message=message,
            data=data,
            errors=None,
        ),
        status=status_code,
    )


def error_response(errors=None, message=DEFAULT_ERROR_MESSAGE, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Returns a DRF Response using the standard error envelope.
    """
    return Response(
        build_response_payload(
            success=False,
            message=message,
            data=None,
            errors=errors or {},
        ),
        status=status_code,
    )


def is_standard_response(data):
    return (
        isinstance(data, dict) and
        {'success', 'message', 'data', 'errors'}.issubset(data.keys())
    )


def is_legacy_response(data):
    return (
        isinstance(data, dict) and
        {'success', 'message', 'data', 'error'}.issubset(data.keys())
    )


def normalize_legacy_response(data):
    """
    Converts the previous `error` envelope key to the standard `errors` key.
    """
    if not is_legacy_response(data):
        return data

    normalized = dict(data)
    normalized['errors'] = normalized.pop('error')
    return normalized
