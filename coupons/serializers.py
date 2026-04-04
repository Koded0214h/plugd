from rest_framework import serializers
from .models import Coupon, UserCouponUsage

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'discount_type', 'discount_value', 'applicable_listings',
            'usage_limit', 'used_count', 'per_user_limit', 'valid_from', 'valid_until',
            'min_order_amount', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'used_count', 'created_at', 'created_by']

    def validate(self, data):
        if data['discount_type'] == 'percentage' and data['discount_value'] > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%.")
        if data['valid_from'] and data['valid_until'] and data['valid_from'] > data['valid_until']:
            raise serializers.ValidationError("valid_from must be before valid_until.")
        return data


class CouponApplySerializer(serializers.Serializer):
    """Serializer for applying coupon at checkout."""
    code = serializers.CharField(max_length=50)

    def validate_code(self, value):
        try:
            coupon = Coupon.objects.get(code=value, is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")
        if not coupon.is_valid:
            raise serializers.ValidationError("This coupon is no longer valid.")
        return value