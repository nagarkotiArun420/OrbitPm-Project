from rest_framework import permissions

class IsInvoiceClientOrManager(permissions.BasePermission):
    """
    Allows only managers/admins, or the client associated with the invoice, to see it.
    """
    def has_object_permission(self, request, view, obj):
        # Admins and Managers have total access
        if request.user.role in ['ADMIN', 'MANAGER']:
            return True
        # Clients can see their own invoices (Read Only)
        return obj.client == request.user and request.method in permissions.SAFE_METHODS
