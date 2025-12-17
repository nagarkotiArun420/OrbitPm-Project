from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model

from accounts.serializers import (
    RegisterSerializer, 
    UserSerializer, 
    CustomTokenObtainPairSerializer
)

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Endpoint for user login. Returns JWT access & refresh tokens along with user information.
    """
    serializer_class = CustomTokenObtainPairSerializer

class CustomTokenRefreshView(TokenRefreshView):
    """
    Endpoint for token refresh.
    """
    pass

class RegisterView(APIView):
    """
    Endpoint for user registration.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user).data
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'data': user_data,
                'error': None
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'success': False,
            'message': 'Registration failed',
            'data': None,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    """
    Endpoint to retrieve or update the authenticated user's profile.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'message': 'Profile details retrieved',
            'data': serializer.data,
            'error': None
        })

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data,
                'error': None
            })
        return Response({
            'success': False,
            'message': 'Profile update failed',
            'data': None,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
