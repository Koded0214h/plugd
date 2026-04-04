from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg # Import Avg for aggregate calculation
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import stripe

from .models import ServiceCategory, ServiceListing, ServiceImage, ServiceRequest, Quote, Review
from .serializers import (
    ServiceListingSerializer, 
    ServiceListingCreateUpdateSerializer,
    ServiceCategorySerializer,
    ServiceRequestSerializer,
    QuoteSerializer,
    ReviewSerializer # Import ReviewSerializer
)
from bookings.models import Booking # Import Booking model for review validation
# Assume Stripe API key is configured in settings.py
stripe.api_key = settings.STRIPE_SECRET_KEY

# Category views (public)
class CategoryListView(generics.ListAPIView):
    """List all active service categories."""
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


# Listing views
class ProviderListingListCreateView(generics.ListCreateAPIView):
    """List all listings for the authenticated provider, or create a new one."""
    serializer_class = ServiceListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'provider':
            return ServiceListing.objects.none()
        return ServiceListing.objects.filter(provider=user)

    def perform_create(self, serializer):
        if self.request.user.role != 'provider':
            raise PermissionDenied("Only providers can create listings.")
        serializer.save(provider=self.request.user)


class ProviderListingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific listing (provider only)."""
    serializer_class = ServiceListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'provider':
            return ServiceListing.objects.none()
        return ServiceListing.objects.filter(provider=user)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceListingCreateUpdateSerializer
        return ServiceListingSerializer


# Public listing views
class PublicListingListView(generics.ListAPIView):
    """List all active service listings (public)."""
    queryset = ServiceListing.objects.filter(is_active=True).select_related('provider', 'category')
    serializer_class = ServiceListingSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'pricing_type', 'is_remote_available']
    search_fields = ['title', 'description', 'provider__business_name']
    ordering_fields = ['price', 'created_at', 'views_count']


class PublicListingDetailView(generics.RetrieveAPIView):
    """Retrieve a single active listing (public)."""
    queryset = ServiceListing.objects.filter(is_active=True)
    serializer_class = ServiceListingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'pk'

    def retrieve(self, request, *args, **kwargs):
        # Increment view count
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        return super().retrieve(request, *args, **kwargs)


# Service Request Views
class ServiceRequestListView(generics.ListCreateAPIView):
    """List service requests (for customer) or create a new one."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return ServiceRequest.objects.filter(customer=user)
        elif user.role == 'provider':
            # Providers can see open requests, possibly filtered by category later
            return ServiceRequest.objects.filter(status='open')
        return ServiceRequest.objects.none()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceRequestSerializer
        return ServiceRequestSerializer # Use same serializer for list and detail

    def perform_create(self, serializer):
        if self.request.user.role != 'customer':
            raise PermissionDenied("Only customers can create service requests.")
        serializer.save(customer=self.request.user)


class ServiceRequestDetailView(generics.RetrieveAPIView):
    """Retrieve a single service request."""
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        # Customers can see their own requests. Providers can see open/in_discussion requests.
        if self.request.user.role == 'customer' and obj.customer != self.request.user:
            raise PermissionDenied("You do not have permission to view this request.")
        if self.request.user.role == 'provider' and obj.status not in ['open', 'in_discussion']:
            raise PermissionDenied("You can only view open or in-discussion requests.")
        return obj


class ServiceRequestUpdateStatusView(generics.UpdateAPIView):
    """Update the status of a service request (e.g., to 'closed', 'cancelled')."""
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.customer != request.user and request.user.role != 'admin':
            raise PermissionDenied("Only the customer or an admin can update the request status.")
        
        # Ensure only valid status transitions are allowed (can be expanded)
        new_status = request.data.get('status')
        if new_status not in ['closed', 'cancelled']:
             raise PermissionDenied("Invalid status transition.")
        
        instance.status = new_status
        instance.save(update_fields=['status', 'updated_at'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

# Quote Views
class QuoteListCreateView(generics.ListCreateAPIView):
    """List quotes for a service request, or create a new quote (provider only)."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['price', 'created_at']
    filterset_fields = ['status']

    def get_queryset(self):
        service_request_id = self.kwargs['service_request_id']
        # Customers can see all quotes for their request. Providers can see their own quotes.
        qs = Quote.objects.filter(service_request_id=service_request_id)
        if self.request.user.role == 'provider':
            qs = qs.filter(provider=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuoteSerializer
        return QuoteSerializer # Use same serializer for list and detail

    def perform_create(self, serializer):
        if self.request.user.role != 'provider':
            raise PermissionDenied("Only providers can submit quotes.")
        
        service_request_id = self.kwargs['service_request_id']
        try:
            service_request = ServiceRequest.objects.get(id=service_request_id)
        except ServiceRequest.DoesNotExist:
            raise serializers.ValidationError("Service request not found.")

        # Check if request is still open for quotes
        if service_request.status not in ['open', 'in_discussion']:
            raise PermissionDenied("This service request is no longer open for quotes.")

        # Check if provider already quoted
        if Quote.objects.filter(service_request=service_request, provider=self.request.user).exists():
            raise PermissionDenied("You have already submitted a quote for this request.")
        
        serializer.save(provider=self.request.user, service_request=service_request)

        # Potentially update service request status to 'in_discussion'
        if service_request.status == 'open':
            service_request.status = 'in_discussion'
            service_request.save(update_fields=['status', 'updated_at'])


class QuoteDetailView(generics.RetrieveAPIView):
    """Retrieve a single quote."""
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        # Customer can see all quotes for their request. Provider can see their own quotes.
        if self.request.user.role == 'customer' and obj.service_request.customer != self.request.user:
            raise PermissionDenied("You do not have permission to view this quote.")
        if self.request.user.role == 'provider' and obj.provider != self.request.user:
            raise PermissionDenied("You do not have permission to view this quote.")
        return obj

class QuoteAcceptView(APIView):
    """Customer accepts a quote, creating a booking."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            quote = Quote.objects.get(id=pk, status='pending')
        except Quote.DoesNotExist:
            return Response({'error': 'Quote not found or not in pending status.'}, status=status.HTTP_404_NOT_FOUND)

        if quote.service_request.customer != request.user:
            raise PermissionDenied("You can only accept quotes for your own service requests.")

        # Ensure the request is still in a state where it can be accepted
        if quote.service_request.status not in ['open', 'in_discussion']:
            return Response({'error': 'This service request is no longer open for quote acceptance.'}, status=status.HTTP_400_BAD_REQUEST)
        
        service_request = quote.service_request
        provider = quote.provider
        customer = service_request.customer

        # --- Start Booking Creation Logic ---
        # Try to find a relevant service listing for the booking.
        # This is an assumption; ideally, the request or quote might link to a specific listing.
        # For now, find any active listing from the provider matching the request's category.
        service_listing = None
        try:
            service_listing = ServiceListing.objects.filter(
                provider=provider,
                category=service_request.category,
                is_active=True
            ).first()
            if not service_listing:
                # If no listing found, we cannot proceed with booking creation as 'listing' is required.
                return Response({'error': 'No active service listing found for this provider and category. Cannot create booking.'}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceListing.DoesNotExist: # This exception is unlikely if .first() is used, but kept for robustness
            return Response({'error': 'No active service listing found for this provider and category. Cannot create booking.'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine booking date, start_time, end_time
        booking_date = service_request.preferred_date
        booking_start_time = service_request.preferred_time

        if not booking_date or not booking_start_time:
            return Response({'error': 'Preferred date and time must be provided in the service request to create a booking.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate end_time based on estimated_duration
        # Assumes estimated_duration is in a format like "5 hours", "2 days", "30 minutes".
        estimated_duration_str = quote.estimated_duration.lower()
        duration_hours = 0
        try:
            if "hour" in estimated_duration_str:
                duration_hours = int(estimated_duration_str.split("hour")[0].strip())
            elif "day" in estimated_duration_str:
                duration_hours = int(estimated_duration_str.split("day")[0].strip()) * 24
            elif "minute" in estimated_duration_str:
                duration_minutes = int(estimated_duration_str.split("minute")[0].strip())
                duration_hours = duration_minutes / 60
            else: # Default to hours if no unit found, or if format is just a number
                 duration_hours = int(estimated_duration_str)
        except (ValueError, AttributeError):
            return Response({'error': 'Invalid or missing estimated duration format. Please provide duration in a parsable format (e.g., "5 hours", "2 days", "30 minutes").'}, status=status.HTTP_400_BAD_REQUEST)

        # Combine date and start_time, then add duration
        # Ensure timezone is handled for datetime objects
        booking_datetime_start = timezone.make_aware(
            datetime.combine(booking_date, booking_start_time)
        )
        booking_end_datetime = booking_datetime_start + timedelta(hours=duration_hours)
        booking_end_time = booking_end_datetime.time()
        
        # Check if provider has completed Stripe onboarding
        if not provider.stripe_account_id or not provider.stripe_onboarding_complete:
            return Response({'error': 'Provider is not ready to receive payments.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate pricing
        total_amount = quote.price
        platform_fee_percentage = Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100
        platform_fee = total_amount * platform_fee_percentage
        provider_amount = total_amount - platform_fee

        # Create Booking object
        # Note: The 'availability' FK is nullable and not directly set here as the quote doesn't map to a specific slot.
        booking = Booking.objects.create(
            listing=service_listing, 
            customer=customer,
            provider=provider,
            date=booking_date,
            start_time=booking_start_time,
            end_time=booking_end_time.time(), # Use calculated end_time
            total_amount=total_amount,
            platform_fee=platform_fee,
            provider_amount=provider_amount,
            status='pending', # Start as pending payment
        )

        # Create Stripe PaymentIntent with Connect
        try:
            # Determine currency: prefer from request budget if available, else from listing.
            # Ensure currency is uppercase as per Stripe's expectation if needed, though lower is often fine.
            currency = quote.service_request.budget.currency if quote.service_request.budget and quote.service_request.budget.currency else service_listing.currency
            
            intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),  # in cents
                currency=currency.lower(),
                application_fee_amount=int(platform_fee * 100),  # platform fee in cents
                transfer_data={
                    'destination': provider.stripe_account_id,  # send rest to provider
                },
                metadata={
                    'booking_id': str(booking.id),
                    'customer_id': str(customer.id),
                    'provider_id': str(provider.id)
                }
            )
            booking.stripe_payment_intent_id = intent.id
            booking.stripe_client_secret = intent.client_secret
            booking.save()
        except stripe.error.StripeError as e:
            # Clean up created booking if Stripe fails
            booking.delete()
            return Response({'error': f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        # --- End Booking Creation Logic ---

        # Update quote status and service request status
        quote.status = 'accepted'
        quote.save(update_fields=['status', 'updated_at'])
        
        service_request.status = 'accepted'
        service_request.save(update_fields=['status', 'updated_at'])
        
        # Return success response with booking creation confirmation
        return Response({
            'message': 'Quote accepted successfully. Booking created and payment initiated.',
            'booking': { # Return relevant booking details
                'id': str(booking.id),
                'stripe_payment_intent_id': booking.stripe_payment_intent_id,
                'stripe_client_secret': booking.stripe_client_secret,
                'total_amount': str(booking.total_amount),
                'status': booking.status,
                'date': str(booking.date),
                'start_time': str(booking.start_time),
                'end_time': str(booking.end_time),
            }
        }, status=status.HTTP_201_CREATED)


class QuoteRejectView(APIView):
    """Provider rejects a quote."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            quote = Quote.objects.get(id=pk, status='pending')
        except Quote.DoesNotExist:
            return Response({'error': 'Quote not found or not in pending status.'}, status=status.HTTP_404_NOT_FOUND)

        if quote.provider != request.user:
            raise PermissionDenied("You can only reject your own quotes.")
        
        quote.status = 'rejected'
        quote.save(update_fields=['status', 'updated_at'])
        
        return Response({'message': 'Quote rejected successfully.'})

# Review Views
class CustomerReviewCreateView(generics.CreateAPIView):
    """Customer creates a review for a completed booking."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        booking = serializer.validated_data.get('booking')

        if user.role != 'customer':
            raise PermissionDenied("Only customers can create reviews.")
        if booking.customer != user:
            raise PermissionDenied("You can only review bookings you made.")
        # Check if booking is in a state that allows review (e.g., 'completed' or 'confirmed' after a grace period)
        # For now, we rely on serializer validation checking for 'confirmed' status.
        # A dedicated 'completed' status and check might be more robust.
        
        serializer.save(customer=user, provider=booking.provider)

class ProviderReviewListView(generics.ListAPIView):
    """List reviews received by a provider."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return Review.objects.filter(provider=user).order_by('-created_at')
        return Review.objects.none()
