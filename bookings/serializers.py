from rest_framework import serializers
from .models import Availability, Booking
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'listing', 'date', 'start_time', 'end_time', 'is_booked']
        read_only_fields = ['id', 'is_booked']

    def validate(self, data):
        # Ensure start_time < end_time
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time.")
        # Ensure date is not in past
        if data['date'] < timezone.now().date():
            raise serializers.ValidationError("Date cannot be in the past.")
        return data


from rest_framework import serializers
from .models import Availability, Booking
from django.utils import timezone
from django.conf import settings

class BookingCreateSerializer(serializers.ModelSerializer):
    availability = serializers.PrimaryKeyRelatedField(queryset=Availability.objects.all())
    date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)

    class Meta:
        model = Booking
        fields = ['listing', 'availability', 'date', 'start_time', 'end_time']

    def validate(self, data):
        listing = data['listing']
        if not listing.is_active:
            raise serializers.ValidationError("This listing is not active.")

        availability = data.get('availability')
        if not availability:
            raise serializers.ValidationError("Availability is required.")

        if availability.is_booked:
            raise serializers.ValidationError("This time slot is already booked.")
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

        return data

    def create(self, validated_data):
        listing = validated_data['listing']
        availability = validated_data['availability']
        provider = listing.provider
        customer = self.context['request'].user

        # Calculate amounts (assuming fixed price for now)
        total = listing.price
        platform_fee = total * (Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100)
        provider_amount = total - platform_fee

        booking = Booking.objects.create(
            listing=listing,
            customer=customer,
            provider=provider,
            availability=availability,
            date=availability.date,
            start_time=availability.start_time,
            end_time=availability.end_time,
            total_amount=total,
            platform_fee=platform_fee,
            provider_amount=provider_amount,
            status='pending'
        )
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