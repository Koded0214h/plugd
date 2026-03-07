from rest_framework import serializers
from .models import ServiceCategory, ServiceListing, ServiceImage

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