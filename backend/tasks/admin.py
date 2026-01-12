from django.contrib import admin
from tasks.models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Professional Django Admin layout for Task instances.
    Provides robust filters, multi-field search, and clean field grouping.
    """
    list_display = (
        'title',
        'project',
        'status',
        'priority',
        'assigned_to',
        'due_date',
        'completed_at',
        'created_at'
    )
    list_filter = ('status', 'priority', 'project', 'due_date')
    search_fields = ('title', 'description', 'slug')
    ordering = ('-created_at',)
    
    readonly_fields = ('id', 'slug', 'completed_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Overview', {
            'fields': ('id', 'title', 'slug', 'description', 'project')
        }),
        ('Workflow & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assigned_by')
        }),
        ('Tracking & Timeline', {
            'fields': ('estimated_hours', 'actual_hours', 'due_date', 'completed_at')
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
