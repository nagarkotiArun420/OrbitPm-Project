import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from projects.models import Project
from invoices.models import Invoice

User = get_user_model()

class InvoiceModelTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Billing Manager',
            role=User.Roles.MANAGER
        )
        self.client = User.objects.create_user(
            email='client@agency.com',
            password='password123',
            full_name='Agency Client',
            role=User.Roles.CLIENT
        )
        self.project = Project.objects.create(
            name='Alpha App',
            owner=self.manager
        )

    def test_create_invoice_successful(self):
        invoice = Invoice.objects.create(
            project=self.project,
            client=self.client,
            amount=2500.00,
            status=Invoice.InvoiceStatus.UNPAID,
            due_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        self.assertEqual(invoice.project, self.project)
        self.assertEqual(invoice.client, self.client)
        self.assertEqual(invoice.amount, 2500.00)
        self.assertEqual(invoice.status, Invoice.InvoiceStatus.UNPAID)
