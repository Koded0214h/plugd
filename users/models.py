from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
import uuid

# Create your models here.

class UserRole(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    PROVIDER = 'provider', 'Service Provider'
    HUB = 'hub', 'Hub (Agency/Coordinator)'
    ADMIN = 'admin', 'Admin'

class VerificationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    VERIFIED = 'verified', 'Verified'
    REJECTED = 'rejected', 'Rejected'

class User(AbstractUser):
    """Custom user model for Plug'd 2.0"""
    
    # Basic Info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(blank=True, null=True)
    
    # Role & Verification
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verification_document = models.ImageField(
        upload_to='verification_docs/',
        blank=True,
        null=True
    )
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_reviewed_at = models.DateTimeField(null=True, blank=True)
    verification_rejection_reason = models.TextField(blank=True)
    
    # Profile
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500)
    location = models.CharField(max_length=255, blank=True)
    
    # Business details (for providers and hubs)
    business_name = models.CharField(max_length=255, blank=True)
    business_address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Stripe Connect
    stripe_account_id = models.CharField(max_length=100, blank=True)
    stripe_onboarding_complete = models.BooleanField(default=False)
    
    # Settings & Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Metadata
    last_active = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Groups and Permissions
    groups = models.ManyToManyField(Group, related_name='custom_user_set', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='custom_user_set', blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # username is still required for AbstractUser
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['verification_status']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.role}"
    
    @property
    def is_verified(self):
        return self.verification_status == VerificationStatus.VERIFIED
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def submit_for_verification(self):
        """Submit user for verification"""
        self.verification_status = VerificationStatus.PENDING
        self.verification_submitted_at = timezone.now()
        self.save()
    
    def verify_user(self):
        """Approve user verification"""
        self.verification_status = VerificationStatus.VERIFIED
        self.verification_reviewed_at = timezone.now()
        self.save()
    
    def reject_verification(self, reason):
        """Reject user verification"""
        self.verification_status = VerificationStatus.REJECTED
        self.verification_rejection_reason = reason
        self.verification_reviewed_at = timezone.now()
        self.save()


class VerificationRequest(models.Model):
    """Track verification requests for admin queue"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_requests')
    document = models.ImageField(upload_to='verification_requests/')
    id_number = models.CharField(max_length=100, blank=True)
    additional_notes = models.TextField(blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_verifications'
    )
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Verification for {self.user.email} - {self.status}"