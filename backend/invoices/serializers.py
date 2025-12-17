from rest_framework import serializers
from invoices.models import Invoice
from accounts.serializers import UserSerializer
from projects.serializers import ProjectSerializer

class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Invoice model.
    """
    client_details = UserSerializer(source='client', read_only=True)
    project_details = ProjectSerializer(source='project', read_only=True)

    class Meta:
        model = Invoice
        fields = (
            'id', 'project', 'project_details', 'client', 'client_details', 
            'amount', 'status', 'due_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
