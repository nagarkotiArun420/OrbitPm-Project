from rest_framework import serializers
from notifications.models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Notification model.
    """
    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'title', 'message', 'is_read', 'created_at')
        read_only_fields = ('id', 'recipient', 'created_at')


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for per-user notification preference settings.
    """
    class Meta:
        model = NotificationPreference
        fields = (
            'task_assignment_enabled',
            'task_comment_enabled',
            'task_deadline_enabled',
            'project_update_enabled',
            'invitation_enabled',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')
