from rest_framework import viewsets, permissions
from tasks.models import Task
from tasks.serializers import TaskSerializer
from tasks.permissions import IsTaskAssigneeOrProjectManager

class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing tasks.
    """
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsTaskAssigneeOrProjectManager]

    def get_queryset(self):
        user = self.request.user
        # Admins/Managers see all tasks; devs see assigned tasks; clients see tasks on their projects
        if user.role in ['ADMIN', 'MANAGER']:
            return Task.objects.all().order_by('-created_at')
        elif user.role == 'DEVELOPER':
            return Task.objects.filter(assigned_to=user).order_by('-created_at')
        else:
            return Task.objects.filter(project__owner=user).order_by('-created_at')
