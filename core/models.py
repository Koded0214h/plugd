import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField
from users.models import User
from django.utils import timezone
from decimal import Decimal
from django.db.models import Avg # Import Avg for aggregate calculation

# --- Service Models ---
class ServiceCategory(models.Model):
    """Service categories like Photography, Videography, etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = CloudinaryField('icon', blank=True, null=True, folder='category_icons/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class ServiceListing(models.Model):
    """Provider's service listing."""
    PRICING_TYPES = [
        ('fixed', 'Fixed Price'),
        ('hourly', 'Hourly Rate'),
        ('daily', 'Daily Rate'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='service_listings',
        limit_choices_to={'role': 'provider'}
    )
    category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='listings'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=5000)
    
    # Pricing
    pricing_type = models.CharField(max_length=10, choices=PRICING_TYPES, default='fixed')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='USD')
    
    # Location (could be text or coordinates – simple for now)
    location = models.CharField(max_length=255, blank=True)
    is_remote_available = models.BooleanField(default=False)
    
    # Media
    featured_image = CloudinaryField('image', blank=True, null=True, folder='service_listings/')
    
    # Metadata
    is_active = models.BooleanField(default=True)
    views_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} by {self.provider.email}"


class ServiceImage(models.Model):
    """Additional images for a service listing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(ServiceListing, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image', folder='service_listings/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.listing.title}"


# --- Review Models ---
class Review(models.Model):
    """Customer review for a completed service."""
    # Define STATUS_CHOICES here, before they are used in the model.
    # These might relate to the booking status itself, or a review status.
    # Based on the context, the review is linked to a Booking.
    # Let's assume the review is created *after* booking is confirmed/completed.
    # We'll use the Booking status for validation.

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        'bookings.Booking', 
        on_delete=models.CASCADE, 
        related_name='review', # Unique related name for booking
        unique=True # A booking can only have one review
    )
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='customer_reviews', # Unique related name for customer
        limit_choices_to={'role': 'customer'}
    )
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='provider_reviews', # Unique related name for provider
        limit_choices_to={'role': 'provider'}
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, max_length=1000)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['provider']),
        ]

    def __str__(self):
        return f"Review for booking {self.booking.id} by {self.customer.email}"


# --- Service Request and Quote Models ---
class ServiceRequest(models.Model):
    """Customer-initiated request for services."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_discussion', 'In Discussion'),
        ('accepted', 'Accepted'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='service_requests',
        limit_choices_to={'role': 'customer'}
    )
    category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='service_requests'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=5000)
    
    # Requirements
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    is_remote_friendly = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"Request: {self.title} by {self.customer.email}"


class Quote(models.Model):
    """Provider's proposal for a ServiceRequest."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(
        ServiceRequest, 
        on_delete=models.CASCADE, 
        related_name='quotes'
    )
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='quotes',
        limit_choices_to={'role': 'provider'}
    )
    
    # Details
    description = models.TextField(max_length=2000)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_duration = models.CharField(max_length=100, blank=True, help_text="e.g., 5 hours, 2 days")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Links
    # When accepted, we might want to link it to a Booking
    # booking = models.OneToOneField('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_quote')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['price']
        unique_together = ['service_request', 'provider'] # One quote per provider per request
        indexes = [
            models.Index(fields=['service_request', 'status']),
            models.Index(fields=['provider']),
        ]

    def __str__(self):
        return f"Quote from {self.provider.email} for {self.service_request.title}"