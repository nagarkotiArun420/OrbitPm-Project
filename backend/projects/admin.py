from django.contrib import admin
from projects.models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Admin configuration for Project model in OrbitPM.
    """
    list_display = ('title', 'status', 'priority', 'manager', 'client', 'deadline', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'deadline')
    search_fields = ('title', 'slug', 'manager__full_name', 'manager__email', 'client__full_name', 'client__email')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)
    
    # Enable search autocomplete for relational FK fields pointing to custom User
    autocomplete_fields = ('manager', 'client', 'created_by')
    
    # Horizontal filter widget for M2M team members
    filter_horizontal = ('team_members',)
    
    readonly_fields = ('created_at', 'updated_at', 'completed_at')

    def save_model(self, request, obj, form, change):
        # Automatically tag creator on creation if not set
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
