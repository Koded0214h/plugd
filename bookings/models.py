import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import User
from core.models import ServiceListing
from bookings.models import ProjectMember

class Availability(models.Model):
    """Provider's available time slots."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availabilities', limit_choices_to={'role': 'provider'})
    listing = models.ForeignKey(ServiceListing, on_delete=models.CASCADE, related_name='availabilities', null=True, blank=True)
    project_member = models.ForeignKey(ProjectMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='availabilities')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Availabilities"
        ordering = ['date', 'start_time']
        unique_together = ['provider', 'date', 'start_time']  # prevent duplicate slots

    def __str__(self):
        return f"{self.provider.email} - {self.date} {self.start_time}-{self.end_time}"


class Booking(models.Model):
    """Booking made by a customer."""
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(ServiceListing, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_as_customer', limit_choices_to={'role': 'customer'})
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_as_provider')
    availability = models.ForeignKey(Availability, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    # Booking details
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Pricing
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    provider_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_client_secret = models.CharField(max_length=255, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['provider', 'date']),
        ]

    def __str__(self):
        return f"Booking {self.id} - {self.customer.email} for {self.listing.title}"


class Transaction(models.Model):
    """Record of financial transactions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='transactions')
    stripe_transaction_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    provider_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='succeeded')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.stripe_transaction_id} - {self.amount} {self.booking.listing.currency}"


class PayoutRequest(models.Model):
    """Record of a provider's request for payout."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='payout_requests',
        limit_choices_to={'role': 'provider'}
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True) # ID of the Stripe transfer
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'status']),
        ]

    def __str__(self):
        return f"Payout request for {self.provider.email} - {self.amount} ({self.status})"


class HubProject(models.Model):
    """A multi-provider project managed by a Hub (Agency)."""
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('ready', 'Ready for Customer'),
        ('accepted', 'Accepted by Customer'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hub = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='managed_projects',
        limit_choices_to={'role': 'hub'}
    )
    customer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='hub_projects',
        limit_choices_to={'role': 'customer'}
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hub', 'status']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"Project: {self.title} (Hub: {self.hub.business_name})"


class ProjectMember(models.Model):
    """A provider invited to or part of a HubProject."""
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('removed', 'Removed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(HubProject, on_delete=models.CASCADE, related_name='members')
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='project_memberships',
        limit_choices_to={'role': 'provider'}
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')

    invited_at = models.DateTimeField(auto_now_add=True)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['project', 'provider']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['provider']),
        ]

    def __str__(self):
        return f"{self.provider.email} in {self.project.title} ({self.status})"


class ProjectPackage(models.Model):
    """A unified package/quote presented by a Hub to a customer."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(HubProject, on_delete=models.CASCADE, related_name='package')

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(help_text="Detailed breakdown of the package for the customer")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Package for {self.project.title} - {self.total_price}"