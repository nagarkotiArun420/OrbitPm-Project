from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Standard serializer for User model.
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role', 'avatar', 'phone_number', 'created_at')
        read_only_fields = ('id', 'created_at')

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'full_name', 'password', 'role', 'phone_number')

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
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
