from django.db.models import Sum
from projects.models import Project
from tasks.models import Task
from invoices.models import Invoice

def calculate_dashboard_metrics(user):
    """
    Decoupled business logic service to compile operational statistics
    customized relative to user authorization and visibility.
    """
    # Base Querysets
    if user.role in ['ADMIN', 'MANAGER']:
        projects = Project.objects.all()
        tasks = Task.objects.all()
        invoices = Invoice.objects.all()
    else:
        projects = Project.objects.filter(owner=user)
        tasks = Task.objects.filter(assigned_to=user)
        invoices = Invoice.objects.filter(client=user)

    total_projects = projects.count()
    active_projects = projects.filter(status=Project.ProjectStatus.ACTIVE).count()
    completed_projects = projects.filter(status=Project.ProjectStatus.COMPLETED).count()

    total_tasks = tasks.count()
    pending_tasks = tasks.exclude(status=Task.TaskStatus.DONE).count()
    completed_tasks = tasks.filter(status=Task.TaskStatus.DONE).count()

    total_revenue = invoices.filter(
        status=Invoice.InvoiceStatus.PAID
    ).aggregate(total=Sum('amount'))['total'] or 0.00
    
    unpaid_revenue = invoices.exclude(
        status=Invoice.InvoiceStatus.PAID
    ).aggregate(total=Sum('amount'))['total'] or 0.00

    return {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'completed_tasks': completed_tasks,
        'total_revenue': total_revenue,
        'unpaid_revenue': unpaid_revenue,
    }
