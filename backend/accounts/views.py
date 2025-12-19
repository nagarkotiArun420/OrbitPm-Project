from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
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
    parser_classes = (MultiPartParser, FormParser, APIView.parser_classes[0]) # Support both JSON and uploads

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

class LogoutView(APIView):
    """
    Endpoint to blacklist the refresh token and sign out the user.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({
                    'success': False,
                    'message': 'Refresh token is required',
                    'data': None,
                    'error': {'code': 'bad_request', 'detail': 'refresh token field is required'}
                }, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Successfully logged out',
                'data': None,
                'error': None
            }, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({
                'success': False,
                'message': 'Invalid token or token already blacklisted',
                'data': None,
                'error': {'code': 'invalid_token', 'detail': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An unexpected error occurred during logout',
                'data': None,
                'error': {'code': 'server_error', 'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
