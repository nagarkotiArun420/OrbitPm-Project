from rest_framework import viewsets, permissions
from teams.models import Team
from teams.serializers import TeamSerializer
from teams.permissions import IsTeamManagerOrAdmin

class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing teams.
    """
    queryset = Team.objects.all().order_by('-created_at')
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'MANAGER']:
            return Team.objects.all().order_by('-created_at')
        return Team.objects.filter(members=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)
