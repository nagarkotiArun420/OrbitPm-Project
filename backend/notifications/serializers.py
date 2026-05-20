from rest_framework import serializers
from notifications.models import Notification
from accounts.serializers import UserMinSerializer


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Notification model.
    Enforces that all fields are read-only except 'is_read'.
    """
    recipient = UserMinSerializer(read_only=True)
    actor = UserMinSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id',
            'recipient',
            'actor',
            'notification_type',
            'title',
            'message',
            'is_read',
            'read_at',
            'metadata',
            'created_at',
        )
        read_only_fields = (
            'id',
            'recipient',
            'actor',
            'notification_type',
            'title',
            'message',
            'read_at',
            'metadata',
            'created_at',
        )
