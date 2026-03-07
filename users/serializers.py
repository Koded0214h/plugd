from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, VerificationRequest, UserRole, ProviderProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password2',
            'first_name', 'last_name', 'phone_number', 'role',
            'business_name'
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
            'business_name': {'required': False},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        
        # Business name required for providers and hubs
        role = attrs.get('role')
        if role in [UserRole.PROVIDER, UserRole.HUB] and not attrs.get('business_name'):
            raise serializers.ValidationError({
                "business_name": "Business name is required for providers and hubs."
            })
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        # Create user
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'), 
                              email=email, password=password)
            
            if not user:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")
        
        data['user'] = user
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer with additional user info"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['verification_status'] = user.verification_status
        token['full_name'] = user.full_name
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra responses
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
            'role': self.user.role,
            'verification_status': self.user.verification_status,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'full_name': self.user.full_name,
            'avatar': self.user.avatar.url if self.user.avatar else None,
        }
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    full_name = serializers.ReadOnlyField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 
            'full_name', 'phone_number', 'role', 'verification_status',
            'avatar', 'avatar_url', 'bio', 'location', 'business_name',
            'business_address', 'tax_id', 'stripe_onboarding_complete',
            'email_notifications', 'sms_notifications', 'last_active',
            'is_online', 'created_at'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'verification_status', 
            'stripe_onboarding_complete', 'created_at'
        ]
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Password fields didn't match."
            })
        return attrs


class VerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for verification requests"""
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.ReadOnlyField(source='user.full_name')
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user', 'user_email', 'user_name', 'document',
            'id_number', 'additional_notes', 'status',
            'rejection_reason', 'created_at', 'reviewed_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'reviewed_at']


class VerificationReviewSerializer(serializers.Serializer):
    """Serializer for reviewing verification requests"""
    status = serializers.ChoiceField(choices=['verified', 'rejected'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if attrs['status'] == 'rejected' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                "rejection_reason": "Rejection reason is required when rejecting a verification."
            })
        return attrs


class ProviderProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    
    class Meta:
        model = ProviderProfile
        fields = [
            'id', 'user', 'user_email', 'user_full_name', 'user_avatar',
            'business_logo', 'business_description', 'years_in_business',
            'website', 'social_links', 'services_offered',
            'average_rating', 'total_reviews', 'completed_bookings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'average_rating', 'total_reviews', 
                            'completed_bookings', 'created_at', 'updated_at']