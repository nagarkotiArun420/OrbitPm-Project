from rest_framework import viewsets, permissions
from projects.models import Project
from projects.serializers import ProjectSerializer
from projects.permissions import IsProjectOwnerOrReadOnly

class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing projects.
    """
    queryset = Project.objects.all().order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrReadOnly]

    def get_queryset(self):
        # Admins and Managers see all projects; developers and clients see projects where they are owner
        user = self.request.user
        if user.role in ['ADMIN', 'MANAGER']:
            return Project.objects.all().order_by('-created_at')
        return Project.objects.filter(owner=user).order_by('-created_at')

    def perform_create(self, serializer):
        # Automatically attach current user as project owner
        serializer.save(owner=self.request.user)
