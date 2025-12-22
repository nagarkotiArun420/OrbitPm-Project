from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom UserAdmin layout for the custom User model.
    """
    # The fields to be displayed in a list in the admin
    list_display = ('email', 'full_name', 'role', 'is_staff', 'is_active', 'created_at')
    
    # Fields to filter by on the right side of the list
    list_filter = ('role', 'is_staff', 'is_active', 'created_at')
    
    # Fields to search by
    search_fields = ('email', 'full_name')
    
    # Ordering of elements
    ordering = ('email',)
    
    # Fieldsets for layout inside editing view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'avatar', 'phone_number')}),
        ('Permissions & Roles', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    # Adding support for django user creation inside admin panel
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password', 'confirm_password'),
        }),
    )
