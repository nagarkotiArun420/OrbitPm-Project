from projects.models import Project

def create_new_project(name, owner, description=None, status=Project.ProjectStatus.PLANNING):
    """
    Decoupled service method for creating a project.
    Triggers actions like initializing a team workspace or sending creation signals.
    """
    project = Project.objects.create(
        name=name,
        owner=owner,
        description=description,
        status=status
    )
    return project

def update_project_status(project_id, new_status):
    """
    Service to update the status of a project.
    """
    project = Project.objects.get(id=project_id)
    project.status = new_status
    project.save()
    return project
