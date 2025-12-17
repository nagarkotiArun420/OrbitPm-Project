import uuid
from django.db import models
from django.conf import settings

class Team(models.Model):
    """
    Team model representing collaborative groups of developers and managers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='managed_teams'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='joined_teams',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
