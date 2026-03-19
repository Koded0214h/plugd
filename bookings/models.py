import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import User
from core.models import ServiceListing

class Availability(models.Model):
    """Provider's available time slots."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availabilities', limit_choices_to={'role': 'provider'})
    listing = models.ForeignKey(ServiceListing, on_delete=models.CASCADE, related_name='availabilities', null=True, blank=True)
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
        return f"Transaction {self.stripe_transaction_id} - {self.amount}"