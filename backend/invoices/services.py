from invoices.models import Invoice

def create_invoice(project, client, amount, due_date):
    """
    Decoupled business logic to issue a new invoice.
    Can hook into PDF generators or email invoice dispatch workers.
    """
    invoice = Invoice.objects.create(
        project=project,
        client=client,
        amount=amount,
        due_date=due_date
    )
    return invoice

def record_invoice_payment(invoice_id):
    """
    Records receipt of payment and sends receipt details.
    """
    invoice = Invoice.objects.get(id=invoice_id)
    invoice.status = Invoice.InvoiceStatus.PAID
    invoice.save()
    return invoice
