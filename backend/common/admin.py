from django.contrib import admin
from common.models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    Django Admin panel configuration for ActivityLog audit records.
    Logs are strictly read-only to guarantee audit integrity.
    """
    list_display = (
        'id',
        'actor',
        'action_type',
        'target_type',
        'target_repr',
        'ip_address',
        'created_at'
    )
    
    list_filter = (
        'action_type',
        'target_type',
        'created_at'
    )
    
    search_fields = (
        'actor__email',
        'actor__full_name',
        'target_id',
        'target_repr',
        'description'
    )
    
    ordering = ('-created_at',)

    # Make all fields read-only
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field.name for field in self.model._meta.fields]
        return []

    # Disable permission to add new logs via admin panel
    def has_add_permission(self, request):
        return False

    # Disable permission to change logs via admin panel
    def has_change_permission(self, request, obj=None):
        return False

    # Disable permission to delete logs via admin panel
    def has_delete_permission(self, request, obj=None):
        return False
