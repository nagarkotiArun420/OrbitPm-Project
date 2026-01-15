from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from notifications.permissions import IsNotificationRecipient
from notifications.services import mark_notification_as_read, mark_all_notifications_as_read


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for viewing and managing in-app notifications.
    Only supports listing, retrieving, and updating (PATCH/PUT) read status.
    Preventing arbitrary POST or DELETE operations.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotificationRecipient]

    def get_queryset(self):
        """
        Users only see notifications sent to them.
        Optimized with select_related for actor and recipient to prevent N+1 queries.
        Utilizes custom recent() queryset helper.
        """
        return Notification.objects.filter(recipient=self.request.user).select_related('recipient', 'actor').recent()

    def perform_update(self, serializer):
        """
        Intercept standard save pipeline and route to business services.
        Ensures is_read state changes manage read_at timestamps correctly.
        """
        is_read = serializer.validated_data.get('is_read')
        if is_read is True:
            # Delegate to our business service to set read_at
            mark_notification_as_read(self.get_object(), request=self.request)
        else:
            serializer.save()

    @action(detail=False, methods=['patch'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """
        Custom PATCH action to mark all notifications for the authenticated user as read.
        """
        count = mark_all_notifications_as_read(request.user, request=request)
        return Response({
            'success': True,
            'message': f'{count} notifications marked as read',
            'data': None,
            'error': None
        }, status=status.HTTP_200_OK)
