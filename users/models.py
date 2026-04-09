import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from cloudinary.models import CloudinaryField
from decimal import Decimal
from django.db.models import Sum, F
from django.apps import apps   # <-- add this import

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

    @property
    def available_balance(self):
        """Calculates the available balance for providers."""
        if self.role != UserRole.PROVIDER:
            return Decimal('0.00')

        Booking = apps.get_model('bookings', 'Booking')
        PayoutRequest = apps.get_model('bookings', 'PayoutRequest')

        confirmed_earnings = Booking.objects.filter(
            provider=self,
            status='confirmed',
            transactions__isnull=False
        ).aggregate(
            total_earned=Sum(F('provider_amount'))
        )['total_earned'] or Decimal('0.00')

        paid_out_amount = PayoutRequest.objects.filter(
            provider=self,
            status='completed'
        ).aggregate(
            total_paid_out=Sum('amount')
        )['total_paid_out'] or Decimal('0.00')

        available = confirmed_earnings - paid_out_amount
        return available.quantize(Decimal('0.01'))

    @property
    def pending_balance(self):
        """Calculates the pending balance for providers."""
        if self.role != UserRole.PROVIDER:
            return Decimal('0.00')

        Booking = apps.get_model('bookings', 'Booking')

        pending_earnings = Booking.objects.filter(
            provider=self,
            status='confirmed',
            transactions__isnull=True
        ).aggregate(
            total_pending=Sum(F('provider_amount'))
        )['total_pending'] or Decimal('0.00')

        return pending_earnings.quantize(Decimal('0.01'))


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


# users/models.py (add to existing imports)

class ProviderProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='provider_profile',
        limit_choices_to={'role': 'provider'}  # optional: restrict to providers
    )
    
    # Business details
    business_logo = CloudinaryField('image', blank=True, null=True, folder='provider_logos/')
    business_description = models.TextField(max_length=2000, blank=True)
    years_in_business = models.PositiveIntegerField(blank=True, null=True)
    website = models.URLField(blank=True, max_length=200)
    
    # Social links (stored as JSON)
    social_links = models.JSONField(default=dict, blank=True)
    
    # Service categories (many-to-many if we have categories, or simple text field for now)
    # We'll implement categories later; for MVP, use a text field or tags.
    services_offered = models.CharField(max_length=500, blank=True, help_text="Comma-separated service categories")
    
    # Stats (calculated, can be updated via signals or periodic tasks)
    average_rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_reviews = models.PositiveIntegerField(default=0)
    completed_bookings = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Provider profile for {self.user.email}"