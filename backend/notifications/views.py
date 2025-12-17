from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from notifications.permissions import IsNotificationRecipient

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and managing in-app notifications.
    """
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotificationRecipient]

    def get_queryset(self):
        # Users only see notifications sent to them
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """
        Custom endpoint to mark all notifications for the authenticated user as read.
        """
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({
            'success': True,
            'message': 'All notifications marked as read',
            'data': None,
            'error': None
        }, status=status.HTTP_200_OK)
