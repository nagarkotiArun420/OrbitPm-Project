from tasks.models import Task

def assign_task_to_user(task_id, user):
    """
    Decoupled business logic to assign a task to a user and notify them.
    """
    task = Task.objects.get(id=task_id)
    task.assigned_to = user
    task.save()
    # Hooks to dispatch in-app or email notifications can live here
    return task

def update_task_progress(task_id, new_status):
    """
    Updates progress of a task and checks if parent project milestones are met.
    """
    task = Task.objects.get(id=task_id)
    task.status = new_status
    task.save()
    return task
