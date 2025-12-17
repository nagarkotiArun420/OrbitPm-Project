from rest_framework.renderers import JSONRenderer

class StandardJSONRenderer(JSONRenderer):
    """
    Standardizes all successful API responses into a unified JSON wrapper:
    {
        "success": true,
        "message": "Operation successful",
        "data": { ... },
        "error": null
    }
    It safely respects pagination and custom error envelopes to prevent double-nesting.
    """
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else 200

        # Check if already enveloped (e.g., from our custom exception handler or paginator)
        if isinstance(data, dict) and 'success' in data and 'error' in data:
            formatted_data = data
        else:
            if 200 <= status_code < 300:
                formatted_data = {
                    'success': True,
                    'message': 'Operation completed successfully',
                    'data': data,
                    'error': None
                }
            else:
                # Fallback in case exception_handler wasn't hit or bypassed
                formatted_data = {
                    'success': False,
                    'message': 'Request could not be processed',
                    'data': None,
                    'error': data
                }

        return super().render(formatted_data, accepted_media_type, renderer_context)
