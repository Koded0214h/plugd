from rest_framework import serializers
from .models import ServiceCategory, ServiceListing, ServiceImage, ServiceRequest, Quote, Review

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['id', 'image', 'caption', 'order']


class ServiceListingSerializer(serializers.ModelSerializer):
    provider_email = serializers.EmailField(source='provider.email', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    provider_avatar = serializers.ImageField(source='provider.avatar', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ServiceImageSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceListing
        fields = [
            'id', 'provider', 'provider_email', 'provider_name', 'provider_avatar',
            'category', 'category_name', 'title', 'description',
            'pricing_type', 'price', 'currency', 'location', 'is_remote_available',
            'featured_image', 'is_active', 'views_count', 'created_at', 'updated_at',
            'images'
        ]
        read_only_fields = ['id', 'provider', 'views_count', 'created_at', 'updated_at']


class ServiceListingCreateUpdateSerializer(serializers.ModelSerializer):
    """Used for write operations (excludes read-only fields)."""
    class Meta:
        model = ServiceListing
        fields = [
            'category', 'title', 'description',
            'pricing_type', 'price', 'currency', 'location', 'is_remote_available',
            'featured_image', 'is_active'
        ]


class QuoteSerializer(serializers.ModelSerializer):
    provider_email = serializers.ReadOnlyField(source='provider.email')
    provider_name = serializers.ReadOnlyField(source='provider.full_name')
    provider_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            'id', 'service_request', 'provider', 'provider_email', 
            'provider_name', 'provider_avatar', 'description', 
            'price', 'estimated_duration', 'status', 
            'created_at', 'updated_at', 'valid_until'
        ]
        read_only_fields = ['id', 'provider', 'status', 'created_at', 'updated_at']

    def get_provider_avatar(self, obj):
        if obj.provider.avatar:
            return obj.provider.avatar.url
        return None


class ServiceRequestSerializer(serializers.ModelSerializer):
    customer_email = serializers.ReadOnlyField(source='customer.email')
    customer_name = serializers.ReadOnlyField(source='customer.full_name')
    category_name = serializers.ReadOnlyField(source='category.name')
    quotes_count = serializers.IntegerField(source='quotes.count', read_only=True)
    my_quote = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'customer', 'customer_email', 'customer_name',
            'category', 'category_name', 'title', 'description',
            'budget', 'location', 'preferred_date', 'preferred_time',
            'is_remote_friendly', 'status', 'quotes_count', 'my_quote',
            'created_at', 'updated_at', 'expires_at'
        ]
        read_only_fields = ['id', 'customer', 'status', 'created_at', 'updated_at']

    def get_my_quote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'provider':
            quote = obj.quotes.filter(provider=request.user).first()
            if quote:
                return QuoteSerializer(quote).data
        return None


class ReviewSerializer(serializers.ModelSerializer):
    customer_email = serializers.ReadOnlyField(source='customer.email')
    provider_email = serializers.ReadOnlyField(source='provider.email')
    customer_name = serializers.ReadOnlyField(source='customer.full_name')
    provider_name = serializers.ReadOnlyField(source='provider.full_name')

    class Meta:
        model = Review
        fields = [
            'id', 'booking', 'customer', 'customer_email', 'customer_name',
            'provider', 'provider_email', 'provider_name', 'rating',
            'comment', 'created_at'
        ]
        read_only_fields = ['id', 'booking', 'customer', 'provider', 'created_at']

    def validate(self, data):
        request = self.context.get('request')
        booking = data.get('booking')

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated.")
        
        # Check if user is the customer of the booking
        if booking.customer != request.user:
            raise serializers.ValidationError("You can only review bookings you made.")
        
        # Check if booking is completed (or in a state allowing review)
        # For now, we'll assume confirmed bookings can be reviewed. A 'completed' status might be better.
        if booking.status not in ['confirmed']: # Consider adding 'completed' status if it exists
            raise serializers.ValidationError("Booking must be confirmed to be reviewed.")

        # Check if a review already exists for this booking
        if Review.objects.filter(booking=booking).exists():
            raise serializers.ValidationError("A review already exists for this booking.")
        
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        booking = validated_data.get('booking')
        
        # Ensure customer and provider are set correctly
        validated_data['customer'] = booking.customer
        validated_data['provider'] = booking.provider
        
        review = super().create(validated_data)
        
        # Update provider's average rating and total reviews count
        provider = review.provider
        # Only consider 'confirmed' bookings for average rating calculation
        provider_reviews = Review.objects.filter(provider=provider, booking__status='confirmed') 
        
        if provider_reviews.exists():
            # Use Avg aggregation from django.db.models
            avg_rating = provider_reviews.aggregate(Avg('rating'))['rating__avg']
            total_reviews = provider_reviews.count()
            
            provider.provider_profile.average_rating = avg_rating
            provider.provider_profile.total_reviews = total_reviews
            provider.provider_profile.save()
        
        return review
