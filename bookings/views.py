import stripe
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework import serializers
from django.utils import timezone
from bookings.models import Transaction
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Availability, Booking
from .serializers import AvailabilitySerializer, BookingCreateSerializer, BookingDetailSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY

# Provider availability management
class AvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return Availability.objects.filter(provider=user, is_booked=False)
        return Availability.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'provider':
            raise PermissionError("Only providers can set availability.")
        serializer.save(provider=self.request.user)


class AvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return Availability.objects.filter(provider=user)
        return Availability.objects.none()


# Customer facing: view available slots for a listing
class ListingAvailableSlotsView(generics.ListAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        listing_id = self.kwargs['listing_id']
        return Availability.objects.filter(
            listing_id=listing_id,
            is_booked=False,
            date__gte=timezone.now().date()
        ).order_by('date', 'start_time')


# Booking creation
class BookingCreateView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        booking = serializer.save()
        # Create Stripe PaymentIntent
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(booking.total_amount * 100),  # in cents
                currency=booking.listing.currency.lower(),
                metadata={
                    'booking_id': str(booking.id),
                    'customer_id': str(booking.customer.id),
                    'provider_id': str(booking.provider.id)
                }
            )
            booking.stripe_payment_intent_id = intent.id
            booking.stripe_client_secret = intent.client_secret
            booking.save()
        except stripe.error.StripeError as e:
            booking.delete()
            raise serializers.ValidationError(f"Stripe error: {str(e)}")


# Get booking details (for customer or provider)
class BookingDetailView(generics.RetrieveAPIView):
    serializer_class = BookingDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Booking.objects.filter(customer=user)
        elif user.role == 'provider':
            return Booking.objects.filter(provider=user)
        return Booking.objects.none()


# List bookings for current user
class UserBookingListView(generics.ListAPIView):
    serializer_class = BookingDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Booking.objects.filter(customer=user).order_by('-created_at')
        elif user.role == 'provider':
            return Booking.objects.filter(provider=user).order_by('-created_at')
        return Booking.objects.none()


# Stripe webhook to confirm payment
class StripeWebhookView(APIView):
    permission_classes = []  # No authentication for webhook

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return Response(status=400)
        except stripe.error.SignatureVerificationError:
            return Response(status=400)

        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            booking_id = payment_intent['metadata']['booking_id']
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = 'confirmed'
                booking.save()
                # Mark availability as booked
                if booking.availability:
                    booking.availability.is_booked = True
                    booking.availability.save()
                # Create transaction record
                Transaction.objects.create(
                    booking=booking,
                    stripe_transaction_id=payment_intent['id'],
                    amount=booking.total_amount,
                    platform_fee=booking.platform_fee,
                    provider_amount=booking.provider_amount
                )
            except Booking.DoesNotExist:
                pass

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            booking_id = payment_intent['metadata']['booking_id']
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = 'cancelled'
                booking.save()
            except Booking.DoesNotExist:
                pass

        return Response(status=200)