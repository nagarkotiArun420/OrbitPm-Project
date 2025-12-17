import logging
from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def global_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework.
    Standardizes error responses to follow the format:
    {
        "success": False,
        "message": "Error description",
        "data": null,
        "error": { ...details... }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        message = "An error occurred while processing your request."
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            message = "Validation failed"
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            message = "Authentication credentials were not provided or are invalid"
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            message = "You do not have permission to perform this action"
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            message = "The requested resource was not found"
            
        # Re-format error response
        response.data = {
            'success': False,
            'message': message,
            'data': None,
            'error': errors
        }
    else:
        # Catch unhandled system exceptions (e.g. database disconnect, coding error)
        logger.exception("Unhandled system exception caught in global handler:")
        
        detail = str(exc) if settings.DEBUG else "A critical server error occurred."
        response = Response({
            'success': False,
            'message': 'Internal Server Error',
            'data': None,
            'error': {
                'non_field_errors': [detail]
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
