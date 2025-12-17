from rest_framework import serializers
from projects.models import Project
from accounts.serializers import UserSerializer

class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the Project model.
    """
    owner_details = UserSerializer(source='owner', read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'status', 'owner', 'owner_details', 'created_at', 'updated_at')
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')
