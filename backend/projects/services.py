from django.db import transaction
from projects.models import Project

@transaction.atomic
def create_project(created_by, **validated_data):
    """
    Service layer method to safely create a Project.
    Encapsulates audit tagging, slug generation, and M2M assignments.
    """
    team_members = validated_data.pop('team_members', [])
    
    # Instantiate the Project with attributes
    project = Project(
        created_by=created_by,
        **validated_data
    )
    # Triggers clean() validation and unique slug resolution on save
    project.save()
    
    # Assign M2M relations after saving the main model
    if team_members:
        project.team_members.set(team_members)
        
    return project


@transaction.atomic
def update_project(project, **validated_data):
    """
    Service layer method to safely update a Project.
    Synchronizes attributes and handles M2M team updates under transactions.
    """
    team_members = validated_data.pop('team_members', None)
    
    # Update baseline attributes
    for field, value in validated_data.items():
        setattr(project, field, value)
        
    project.save()
    
    # If team members are supplied in update payload, override current members
    if team_members is not None:
        project.team_members.set(team_members)
        
    return project


@transaction.atomic
def delete_project(project):
    """
    Service layer method to safely delete a Project.
    Ensures safe operations.
    """
    project.delete()
