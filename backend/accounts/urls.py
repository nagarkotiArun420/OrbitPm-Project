from django.urls import path
from accounts.views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    RegisterView,
    UserProfileView
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='auth_refresh'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', UserProfileView.as_view(), name='auth_me'),
]
