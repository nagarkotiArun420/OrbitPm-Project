from rest_framework import serializers
from tasks.models import Task
from accounts.serializers import UserSerializer

class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the Task model.
    """
    assignee_details = UserSerializer(source='assigned_to', read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'project', 'assigned_to', 
            'assignee_details', 'status', 'priority', 'due_date', 
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
