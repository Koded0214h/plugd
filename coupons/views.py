from decimal import Decimal
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Coupon, UserCouponUsage
from .serializers import CouponSerializer, CouponApplySerializer

# Provider coupon management
class ProviderCouponListCreateView(generics.ListCreateAPIView):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return Coupon.objects.filter(created_by=user)
        return Coupon.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'provider':
            raise PermissionDenied("Only providers can create coupons.")
        serializer.save(created_by=self.request.user)


class ProviderCouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return Coupon.objects.filter(created_by=user)
        return Coupon.objects.none()


# Admin coupon management (global coupons)
class AdminCouponListCreateView(generics.ListCreateAPIView):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        # Admin can see all coupons (optional filter)
        return Coupon.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminCouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Coupon.objects.all()


# Public endpoint to check coupon validity and apply discount
class CouponApplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CouponApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        coupon = get_object_or_404(Coupon, code=code)

        # Check per-user usage limit
        user_usage_count = UserCouponUsage.objects.filter(user=request.user, coupon=coupon).count()
        if user_usage_count >= coupon.per_user_limit:
            return Response({'error': 'You have already used this coupon the maximum number of times.'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: get total amount from request (e.g., booking total)
        total_amount = request.data.get('total_amount')
        if total_amount and coupon.min_order_amount and Decimal(total_amount) < coupon.min_order_amount:
            return Response({'error': f'Minimum order amount of {coupon.min_order_amount} required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate discounted amount
        discounted = coupon.apply_discount(Decimal(total_amount) if total_amount else 0)

        return Response({
            'coupon': CouponSerializer(coupon).data,
            'original_amount': total_amount,
            'discounted_amount': str(discounted),
            'message': 'Coupon is valid.'
        })