import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import User
from core.models import ServiceListing

class Coupon(models.Model):
    """Base coupon model (admin or provider created)."""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Who created this coupon
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_coupons')
    # For provider coupons, this is the provider; for admin, it's the admin.
    # We can differentiate by role.
    
    # Applicability
    applicable_listings = models.ManyToManyField(ServiceListing, blank=True, related_name='coupons')
    # If empty, applies to all listings (global coupon)
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(default=1, help_text="Maximum number of times this coupon can be used.")
    used_count = models.PositiveIntegerField(default=0)
    
    # Per-user limit
    per_user_limit = models.PositiveIntegerField(default=1, help_text="How many times a single user can use this coupon.")
    
    # Expiration
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    
    # Minimum order amount (optional)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Who can use: all customers, or specific customers?
    # For user-specific coupons, we'll use a separate model.
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()} {self.discount_value})"

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if now < self.valid_from:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def apply_discount(self, total_amount):
        """Return discounted amount."""
        if self.discount_type == 'percentage':
            discount = total_amount * (self.discount_value / 100)
            return max(total_amount - discount, 0)
        else:  # fixed
            return max(total_amount - self.discount_value, 0)


class UserCouponUsage(models.Model):
    """Track usage per user per coupon."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    used_at = models.DateTimeField(auto_now_add=True)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='coupon_usage', null=True)

    class Meta:
        unique_together = ['user', 'coupon']

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code}"