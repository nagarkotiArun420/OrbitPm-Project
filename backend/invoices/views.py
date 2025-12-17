from rest_framework import viewsets, permissions
from invoices.models import Invoice
from invoices.serializers import InvoiceSerializer
from invoices.permissions import IsInvoiceClientOrManager

class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing invoices.
    """
    queryset = Invoice.objects.all().order_by('-created_at')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsInvoiceClientOrManager]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'MANAGER']:
            return Invoice.objects.all().order_by('-created_at')
        # Clients see only their invoices
        return Invoice.objects.filter(client=user).order_by('-created_at')
