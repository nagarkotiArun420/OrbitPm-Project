from rest_framework import serializers
from notifications.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Notification model.
    """
    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'title', 'message', 'is_read', 'created_at')
        read_only_fields = ('id', 'recipient', 'created_at')
