from rest_framework import serializers
from teams.models import Team
from accounts.serializers import UserSerializer

class TeamSerializer(serializers.ModelSerializer):
    """
    Serializer for Team model.
    """
    manager_details = UserSerializer(source='manager', read_only=True)
    members_details = UserSerializer(source='members', many=True, read_only=True)

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'description', 'manager', 'manager_details', 
            'members', 'members_details', 'created_at'
        )
        read_only_fields = ('id', 'created_at')
