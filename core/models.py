import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField
from users.models import User

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