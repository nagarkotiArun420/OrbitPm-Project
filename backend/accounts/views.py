import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
from common.services import log_activity
from common.constants import ActionType, TargetType
from common.responses import error_response, success_response
from common.throttling import LoginRateThrottle, RegisterRateThrottle
from common.utils import get_client_ip

from accounts.serializers import (
    RegisterSerializer, 
    UserSerializer, 
    CustomTokenObtainPairSerializer
)

User = get_user_model()
logger = logging.getLogger('accounts')

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Endpoint for user login. Returns JWT access & refresh tokens along with user information.
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        except Exception as e:
            # Log failed login attempt
            email = request.data.get('email', 'unknown')
            ip = get_client_ip(request)
            logger.warning(
                "Failed login attempt for email=%s from IP=%s",
                email, ip
            )
            raise e

        user = serializer.user
        
        # Log successful login
        log_activity(
            actor=user,
            action_type=ActionType.LOGIN,
            target_type=TargetType.USER,
            target_id=str(user.id),
            target_repr=user.email,
            description=f"User {user.email} logged in successfully.",
            request=request
        )

        return success_response(serializer.validated_data, message='Login successful')

class CustomTokenRefreshView(TokenRefreshView):
    """
    Endpoint for token refresh.
    """
    throttle_classes = [LoginRateThrottle]

class RegisterView(APIView):
    """
    Endpoint for user registration.
    """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [RegisterRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user).data
            return success_response(
                data=user_data,
                message='User registered successfully',
                status_code=status.HTTP_201_CREATED
            )
            
        return error_response(
            errors=serializer.errors,
            message='Registration failed',
            status_code=status.HTTP_400_BAD_REQUEST
        )

class UserProfileView(APIView):
    """
    Endpoint to retrieve or update the authenticated user's profile.
    """
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser, APIView.parser_classes[0]) # Support both JSON and uploads

    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(serializer.data, message='Profile details retrieved')

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data, message='Profile updated successfully')
        return error_response(
            errors=serializer.errors,
            message='Profile update failed',
            status_code=status.HTTP_400_BAD_REQUEST
        )

class LogoutView(APIView):
    """
    Endpoint to blacklist the refresh token and sign out the user.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return error_response(
                    errors={'code': 'bad_request', 'detail': 'refresh token field is required'},
                    message='Refresh token is required',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Log logout event
            user = request.user
            log_activity(
                actor=user,
                action_type=ActionType.LOGOUT,
                target_type=TargetType.USER,
                target_id=str(user.id),
                target_repr=user.email,
                description=f"User {user.email} logged out.",
                request=request
            )
            
            return success_response(message='Successfully logged out')
        except TokenError as e:
            return error_response(
                errors={'code': 'invalid_token', 'detail': str(e)},
                message='Invalid token or token already blacklisted',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                errors={'code': 'server_error', 'detail': str(e)},
                message='An unexpected error occurred during logout',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
