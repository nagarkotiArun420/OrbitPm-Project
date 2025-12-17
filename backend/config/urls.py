from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Global API Versioning Prefix
api_prefix = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path(f'{api_prefix}auth/', include('accounts.urls')),
    path(f'{api_prefix}projects/', include('projects.urls')),
    path(f'{api_prefix}tasks/', include('tasks.urls')),
    path(f'{api_prefix}teams/', include('teams.urls')),
    path(f'{api_prefix}invoices/', include('invoices.urls')),
    path(f'{api_prefix}notifications/', include('notifications.urls')),
    path(f'{api_prefix}analytics/', include('analytics.urls')),
]

# Serve static/media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
