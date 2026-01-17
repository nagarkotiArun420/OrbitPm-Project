from rest_framework.renderers import JSONRenderer
from common.responses import (
    DEFAULT_ERROR_MESSAGE,
    DEFAULT_SUCCESS_MESSAGE,
    build_response_payload,
    is_legacy_response,
    is_standard_response,
    normalize_legacy_response,
)

class StandardJSONRenderer(JSONRenderer):
    """
    Standardizes all successful API responses into a unified JSON wrapper:
    {
        "success": true,
        "message": "Operation successful",
        "data": { ... },
        "errors": null
    }
    It safely respects pagination and custom error envelopes to prevent double-nesting.
    """
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else 200

        # Check if already enveloped (e.g., from our custom exception handler or paginator).
        if is_standard_response(data):
            formatted_data = data
        elif is_legacy_response(data):
            formatted_data = normalize_legacy_response(data)
        else:
            if 200 <= status_code < 300:
                formatted_data = build_response_payload(
                    success=True,
                    message=DEFAULT_SUCCESS_MESSAGE,
                    data=data,
                    errors=None,
                )
            else:
                # Fallback in case exception_handler wasn't hit or bypassed
                formatted_data = build_response_payload(
                    success=False,
                    message=DEFAULT_ERROR_MESSAGE,
                    data=None,
                    errors=data,
                )

        return super().render(formatted_data, accepted_media_type, renderer_context)
