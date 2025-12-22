import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from accounts.services import create_user_profile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Standard serializer for User model.
    """
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role', 'avatar', 'phone_number', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'full_name', 'password', 'confirm_password', 'role', 'phone_number')

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        password = data['password']
        
        # Strong password validation (length, uppercase, lowercase, numbers, special character)
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})
        if not re.search(r"[A-Z]", password):
            raise serializers.ValidationError({"password": "Password must contain at least one uppercase letter."})
        if not re.search(r"[a-z]", password):
            raise serializers.ValidationError({"password": "Password must contain at least one lowercase letter."})
        if not re.search(r"[0-9]", password):
            raise serializers.ValidationError({"password": "Password must contain at least one number."})
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise serializers.ValidationError({"password": "Password must contain at least one special character."})

        # Run django's password validators too
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = create_user_profile(
            email=validated_data['email'],
            password=password,
            full_name=validated_data['full_name'],
            role=validated_data.get('role', User.Roles.DEVELOPER),
            phone_number=validated_data.get('phone_number')
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Token Serializer that appends user payload data inside the response,
    avoiding extra network requests from the frontend after initial login.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims in JWT payload
        token['email'] = user.email
        token['role'] = user.role
        token['full_name'] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Include full user details in the HTTP response body
        data['user'] = UserSerializer(self.user).data
        return data

class UserMinSerializer(serializers.ModelSerializer):
    """
    Lightweight, read-only serializer for nested user relations.
    Excludes sensitive attributes to ensure robust security borders.
    """
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role', 'avatar')
        read_only_fields = fields
