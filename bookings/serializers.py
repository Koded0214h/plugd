import stripe
from rest_framework import serializers
from .models import Availability, Booking, Transaction, PayoutRequest                                                                                               
from decimal import Decimal                                                                                                                                         
from django.conf import settings                                                                                                                                    
from django.utils import timezone                                                                                                                                   
from django.db.models import Sum, F   
from users.serializers import UserSummarySerializer
from .models import Availability, Booking, Transaction, PayoutRequest, HubProject, ProjectMember, ProjectPackage
from coupons.models import Coupon, UserCouponUsage

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'listing', 'date', 'start_time', 'end_time', 'is_booked', 'project_member']
        read_only_fields = ['id', 'is_booked']

    def validate(self, data):
        # Ensure start_time < end_time
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time.")
        # Ensure date is not in past
        if data['date'] < timezone.now().date():
            raise serializers.ValidationError("Date cannot be in the past.")
        return data


# bookings/serializers.py (add/modify the following)
class BookingCreateSerializer(serializers.ModelSerializer):
    availability = serializers.PrimaryKeyRelatedField(queryset=Availability.objects.all())
    date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    coupon_code = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Booking
        fields = ['listing', 'availability', 'date', 'start_time', 'end_time', 'coupon_code']

    def validate(self, data):
        listing = data['listing']
        if not listing.is_active:
            raise serializers.ValidationError("This listing is not active.")

        availability = data.get('availability')
        if not availability:
            raise serializers.ValidationError("Availability is required.")

        # Check if slot is already booked
        if availability.is_booked:
            raise serializers.ValidationError("This time slot is already booked.")

        # Check if slot is reserved (locked) by another checkout
        if availability.reserved_until and availability.reserved_until > timezone.now():
            raise serializers.ValidationError(
                "This time slot is currently being processed by another customer. Please try again in a few minutes."
            )

        if availability.provider != listing.provider:
            raise serializers.ValidationError("Availability does not belong to this listing's provider.")

        # Populate date/time from availability
        data['date'] = availability.date
        data['start_time'] = availability.start_time
        data['end_time'] = availability.end_time

        # Check for double booking (including pending/confirmed)
        conflicting = Booking.objects.filter(
            provider=listing.provider,
            date=data['date'],
            start_time=data['start_time'],
            status__in=['pending', 'confirmed']
        ).exists()
        if conflicting:
            raise serializers.ValidationError("This time slot is already booked.")

        # --- Coupon handling ---
        coupon_code = data.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            except Coupon.DoesNotExist:
                raise serializers.ValidationError("Invalid coupon code.")
            if not coupon.is_valid:
                raise serializers.ValidationError("This coupon is no longer valid.")

            user = self.context['request'].user
            user_usage = UserCouponUsage.objects.filter(user=user, coupon=coupon).count()
            if user_usage >= coupon.per_user_limit:
                raise serializers.ValidationError(
                    "You have already used this coupon the maximum number of times."
                )

            # Check if coupon applies to this listing
            if coupon.applicable_listings.exists() and not coupon.applicable_listings.filter(id=listing.id).exists():
                raise serializers.ValidationError("This coupon is not applicable to this service.")

            # Check minimum order amount
            total = listing.price
            if coupon.min_order_amount and total < coupon.min_order_amount:
                raise serializers.ValidationError(
                    f"Minimum order amount of {coupon.min_order_amount} required for this coupon."
                )

            # Calculate discounted total
            discounted_total = coupon.apply_discount(total)
            data['discounted_total'] = discounted_total
            data['coupon'] = coupon
        else:
            data['discounted_total'] = listing.price
            data['coupon'] = None

        return data

    def create(self, validated_data):
        listing = validated_data['listing']
        provider = listing.provider
        customer = self.context['request'].user
        coupon = validated_data.get('coupon')
        discounted_total = validated_data['discounted_total']

        # Check if provider has completed Stripe onboarding (only needed for instant bookings)
        if listing.booking_approval_type == 'instant':
            if not provider.stripe_account_id or not provider.stripe_onboarding_complete:
                raise serializers.ValidationError("Provider is not ready to receive payments.")

        # Calculate amounts using discounted total
        platform_fee = discounted_total * (Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100)
        provider_amount = discounted_total - platform_fee

        # Determine initial status
        initial_status = 'pending_approval' if listing.booking_approval_type == 'manual' else 'pending'

        # Create booking
        booking = Booking.objects.create(
            listing=listing,
            customer=customer,
            provider=provider,
            availability=validated_data['availability'],
            date=validated_data['date'],
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],
            total_amount=discounted_total,
            platform_fee=platform_fee,
            provider_amount=provider_amount,
            status=initial_status
        )

        # Reserve the slot for 15 minutes
        availability = validated_data['availability']
        availability.reserved_until = timezone.now() + timezone.timedelta(minutes=15)
        availability.save(update_fields=['reserved_until'])

        # Record coupon usage
        if coupon:
            UserCouponUsage.objects.create(user=customer, coupon=coupon, booking=booking)
            coupon.used_count += 1
            coupon.save(update_fields=['used_count'])

        # Create Stripe PaymentIntent only for instant bookings
        if listing.booking_approval_type == 'instant':
            try:
                metadata = {
                    'booking_id': str(booking.id),
                    'customer_id': str(customer.id),
                    'provider_id': str(provider.id),
                }
                if coupon:
                    metadata['coupon_code'] = coupon.code

                intent = stripe.PaymentIntent.create(
                    amount=int(discounted_total * 100),
                    currency=listing.currency.lower(),
                    application_fee_amount=int(platform_fee * 100),
                    transfer_data={'destination': provider.stripe_account_id},
                    metadata=metadata
                )
                booking.stripe_payment_intent_id = intent.id
                booking.stripe_client_secret = intent.client_secret
                booking.save()
            except stripe.error.StripeError as e:
                booking.delete()
                raise serializers.ValidationError(f"Stripe error: {str(e)}")

        return booking



class BookingDetailSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'listing', 'listing_title', 'customer', 'customer_name',
            'provider', 'provider_name', 'date', 'start_time', 'end_time',
            'total_amount', 'platform_fee', 'provider_amount',
            'stripe_payment_intent_id', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'stripe_payment_intent_id', 'status', 'created_at']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'booking', 'stripe_transaction_id', 'amount', 'platform_fee', 'provider_amount', 'status', 'created_at']
        read_only_fields = ['id', 'booking', 'stripe_transaction_id', 'amount', 'platform_fee', 'provider_amount', 'status', 'created_at']

class PayoutRequestSerializer(serializers.ModelSerializer):
    provider_email = serializers.ReadOnlyField(source='provider.email')
    provider_name = serializers.ReadOnlyField(source='provider.full_name')
    
    class Meta:
        model = PayoutRequest
        fields = [
            'id', 'provider', 'provider_email', 'provider_name', 'amount', 
            'status', 'stripe_transfer_id', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'provider', 'status', 'stripe_transfer_id', 'created_at', 'processed_at']

    def validate(self, data):
        # Ensure amount is positive
        if data.get('amount') and data['amount'] <= 0:
            raise serializers.ValidationError("Payout amount must be positive.")
        
        # Check if provider has sufficient balance (this logic would typically be in the view/service)
        # For serializer, we mainly validate data integrity. Balance check is more of a business logic.
        return data

    # This serializer is primarily for reading/displaying payout requests.
    # Creation and modification logic will be handled in the views.


class ProjectMemberSerializer(serializers.ModelSerializer):
    provider_details = UserSummarySerializer(source='provider', read_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'project', 'provider', 'provider_details', 'status', 'invited_at', 'joined_at']
        read_only_fields = ['id', 'project', 'status', 'invited_at', 'joined_at']


class ProjectPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPackage
        fields = ['id', 'project', 'total_price', 'description', 'status', 'expires_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']


class HubProjectSerializer(serializers.ModelSerializer):
    hub_details = UserSummarySerializer(source='hub', read_only=True)
    customer_details = UserSummarySerializer(source='customer', read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    package = ProjectPackageSerializer(read_only=True)
    
    class Meta:
        model = HubProject
        fields = [
            'id', 'hub', 'hub_details', 'customer', 'customer_details',
            'title', 'description', 'budget', 'status', 
            'members', 'package', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'hub', 'created_at', 'updated_at']

    def validate_customer(self, value):
        if value and value.role != 'customer':
            raise serializers.ValidationError("Only customers can be assigned to a project.")
        return value


class PlatformRevenueSerializer(serializers.Serializer):
    total_platform_earnings = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_payouts = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    net_revenue = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    pending_payouts = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_bookings = serializers.IntegerField(read_only=True)
    total_transactions = serializers.IntegerField(read_only=True)
    new_users_count = serializers.IntegerField(read_only=True)

