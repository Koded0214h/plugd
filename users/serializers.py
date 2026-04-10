from rest_framework import serializers
from .models import User, VerificationRequest, ProviderProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['is_verified'] = user.is_verified
        # ... you can add more claims here

        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."}) # type: ignore
        validate_email(attrs['email'])
        from .models import UserRole
        if attrs.get('role') == UserRole.ADMIN:
            raise serializers.ValidationError({"role": "Cannot register as admin via this endpoint."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data['role'],
            username=validated_data['email'] # Use email as username
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class AdminRegisterSerializer(RegisterSerializer):
    """Admin registration serializer - always creates admin users"""

    class Meta(RegisterSerializer.Meta):
        fields = RegisterSerializer.Meta.fields

    def create(self, validated_data):
        from .models import UserRole, VerificationStatus
        validated_data['role'] = UserRole.ADMIN
        user = super().create(validated_data)
        user.is_staff = True
        user.is_active = True
        user.verification_status = VerificationStatus.VERIFIED
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name', 'role',
            'phone_number', 'avatar', 'bio', 'location',
            'verification_status', 'is_active', 'is_online', 'last_active',
            'created_at', 'updated_at', 'stripe_account_id', 'stripe_onboarding_complete',
            'email_notifications', 'sms_notifications', 'business_name', 'business_address', 'tax_id'
        )
        read_only_fields = (
            'id', 'email', 'role', 'verification_status', 'is_active',
            'is_online', 'last_active', 'created_at', 'updated_at',
            'stripe_account_id', 'stripe_onboarding_complete'
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


class VerificationRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    user_full_name = serializers.ReadOnlyField(source='user.full_name')
    document = serializers.URLField(read_only=True)

    class Meta:
        model = VerificationRequest
        fields = (
            'id', 'user', 'user_email', 'user_full_name', 'document', 
            'id_number', 'additional_notes', 'status', 'reviewed_by', 
            'rejection_reason', 'created_at', 'reviewed_at'
        )
        read_only_fields = (
            'id', 'user', 'user_email', 'user_full_name', 'status', 
            'reviewed_by', 'reviewed_at', 'created_at', 'rejection_reason'
        )


class AdminVerificationReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=('verified', 'rejected'))
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class ProviderProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    user_full_name = serializers.ReadOnlyField(source='user.full_name')
    user_avatar = serializers.SerializerMethodField()
    business_logo = serializers.SerializerMethodField()
    user_location = serializers.ReadOnlyField(source='user.location')
    user_is_online = serializers.ReadOnlyField(source='user.is_online')
    user_last_active = serializers.DateTimeField(source='user.last_active', read_only=True)
    user_stripe_onboarding_complete = serializers.BooleanField(source='user.stripe_onboarding_complete', read_only=True)

    def get_user_avatar(self, obj):
        if obj.user.avatar:
            return obj.user.avatar.url
        return None

    def get_business_logo(self, obj):
        if obj.business_logo:
            return obj.business_logo.url
        return None

    class Meta:
        model = ProviderProfile
        fields = (
            'id', 'user', 'user_email', 'user_full_name', 'user_avatar',
            'user_location', 'user_is_online', 'user_last_active',
            'user_stripe_onboarding_complete', 'business_logo', 'business_description',
            'years_in_business', 'website', 'social_links', 'services_offered',
            'average_rating', 'total_reviews', 'completed_bookings',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'user', 'user_email', 'user_full_name', 'user_avatar', 
            'user_location', 'user_is_online', 'user_last_active', 
            'user_stripe_onboarding_complete', 'average_rating', 
            'total_reviews', 'completed_bookings', 'created_at', 'updated_at'
        )


class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id', 'full_name', 'email', 'role', 
            'verification_status', 'is_active', 'created_at'
        )

class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'full_name', 'avatar', 'role')
        read_only_fields = ('id', 'first_name', 'last_name', 'full_name', 'avatar', 'role')

class ProviderBalanceSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    pending_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = ('available_balance', 'pending_balance')
