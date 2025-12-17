import uuid
from django.db import models
from django.conf import settings
from projects.models import Project

class Invoice(models.Model):
    """
    Invoice model representing billing entities for client projects.
    """
    class InvoiceStatus(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PAID = 'PAID', 'Paid'
        OVERDUE = 'OVERDUE', 'Overdue'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='invoices'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, 
        choices=InvoiceStatus.choices, 
        default=InvoiceStatus.UNPAID
    )
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.id[:8]} - {self.project.name} (${self.amount})"
