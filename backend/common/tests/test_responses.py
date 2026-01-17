from django.test import SimpleTestCase
from rest_framework import status

from common.responses import (
    error_response,
    normalize_legacy_response,
    success_response,
)


class APIResponseHelperTests(SimpleTestCase):
    def test_success_response_uses_standard_envelope(self):
        response = success_response(
            data={'id': '123'},
            message='Created',
            status_code=status.HTTP_201_CREATED,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['message'], 'Created')
        self.assertEqual(response.data['data'], {'id': '123'})
        self.assertIsNone(response.data['errors'])

    def test_error_response_uses_standard_envelope(self):
        response = error_response(
            errors={'name': ['This field is required.']},
            message='Validation failed',
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIsNone(response.data['data'])
        self.assertEqual(response.data['errors']['name'], ['This field is required.'])

    def test_legacy_error_key_is_normalized(self):
        payload = normalize_legacy_response({
            'success': False,
            'message': 'Old response',
            'data': None,
            'error': {'detail': 'Nope'},
        })

        self.assertNotIn('error', payload)
        self.assertEqual(payload['errors'], {'detail': 'Nope'})
