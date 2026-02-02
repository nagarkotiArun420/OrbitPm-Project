from rest_framework import permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from common.responses import success_response
from common.throttling import WriteOperationThrottle, UserBurstThrottle, UserSustainedThrottle
from notifications.models import Notification
from notifications.serializers import NotificationPreferenceSerializer, NotificationSerializer
from notifications.permissions import IsNotificationRecipient
from notifications.services import get_user_preferences

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and managing in-app notifications.
    """
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotificationRecipient]
    throttle_classes = [WriteOperationThrottle, UserBurstThrottle, UserSustainedThrottle]

    def get_queryset(self):
        # Users only see notifications sent to them
        return Notification.objects.filter(recipient=self.request.user).only(
            'id', 'recipient_id', 'title', 'message', 'is_read', 'created_at'
        ).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """
        Custom endpoint to mark all notifications for the authenticated user as read.
        """
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return success_response(
            message='All notifications marked as read',
            status_code=status.HTTP_200_OK
        )


class NotificationPreferenceView(APIView):
    """
    Retrieve and update the authenticated user's notification preferences.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        prefs = get_user_preferences(request.user)
        return success_response(
            data=NotificationPreferenceSerializer(prefs).data,
            message='Notification preferences retrieved successfully',
        )

    def patch(self, request):
        prefs = get_user_preferences(request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Notification preferences updated successfully',
        )

    def put(self, request):
        prefs = get_user_preferences(request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Notification preferences updated successfully',
        )
