from rest_framework import permissions

class IsNotificationRecipient(permissions.BasePermission):
    """
    Ensures that notifications are only accessible by the direct recipient.
    """
    def has_object_permission(self, request, view, obj):
        return obj.recipient_id == request.user.id
