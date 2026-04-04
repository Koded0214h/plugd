from decimal import Decimal
from rest_framework.exceptions import PermissionDenied
import stripe
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework import serializers 
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Sum, F
from django.utils import timezone

from bookings.models import Availability, Booking, Transaction, PayoutRequest, HubProject, ProjectMember, ProjectPackage
from bookings.serializers import (
    AvailabilitySerializer, BookingCreateSerializer, BookingDetailSerializer, 
    TransactionSerializer, PayoutRequestSerializer,
    HubProjectSerializer, ProjectMemberSerializer, ProjectPackageSerializer,
    PlatformRevenueSerializer # Add PlatformRevenueSerializer
)
from users.models import User # Import User model for role checks
from users.serializers import ProviderBalanceSerializer, UserProfileSerializer # Add UserProfileSerializer

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
                # Mark availability as booked if it exists
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
                pass # Booking not found, ignore

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            booking_id = payment_intent['metadata']['booking_id']
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = 'cancelled'
                booking.save()
            except Booking.DoesNotExist:
                pass # Booking not found, ignore

        return Response(status=200)

# Payouts
class ProviderPayoutRequestView(generics.ListCreateAPIView):
    """
    Allows providers to view their payout history and request a new payout.
    """
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return PayoutRequest.objects.filter(provider=user)
        return PayoutRequest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'provider':
            raise PermissionDenied("Only providers can request payouts.")

        # Check if provider has completed Stripe onboarding
        if not user.stripe_account_id or not user.stripe_onboarding_complete:
            raise PermissionDenied("Stripe onboarding must be completed before requesting payouts.")

        requested_amount = serializer.validated_data.get('amount')
        
        if not requested_amount or requested_amount <= 0:
            raise serializers.ValidationError("Payout amount must be positive.")
        
        # --- Balance Check (Placeholder) ---
        # In a real system, this would check against an actual available balance.
        # This requires summing up 'provider_amount' from completed bookings not yet paid out.
        # For this example, we'll assume the requested amount is valid if positive.
        # A minimum payout amount might also be enforced.
        # --- End Placeholder ---

        serializer.save(provider=user, amount=requested_amount, status='pending')
        # NOTE: Stripe transfer creation is not automated by this request view.
        # It creates a pending request that can be reviewed/processed by admins or a separate background job.
        # For a fully automated system, Stripe Transfer API call would happen here.


class AdminPayoutListView(generics.ListAPIView):
    """Admin view for all payout requests."""
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can access this

    def get_queryset(self):
            return PayoutRequest.objects.all().order_by('-created_at')

# --- Payout Request Logic ---
class ProviderPayoutRequestView(generics.ListCreateAPIView):
    """
    Allows providers to view their payout history and request a new payout.
    Also initiates Stripe transfer upon successful request.
    """
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'provider':
            return PayoutRequest.objects.filter(provider=user)
        return PayoutRequest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'provider':
            raise PermissionDenied("Only providers can request payouts.")

        # Check if provider has completed Stripe onboarding
        if not user.stripe_account_id or not user.stripe_onboarding_complete:
            raise PermissionDenied("Stripe onboarding must be completed before requesting payouts.")

        requested_amount = serializer.validated_data.get('amount')
        
        if not requested_amount or requested_amount <= 0:
            raise serializers.ValidationError("Payout amount must be positive.")
        
        # Calculate available balance for the provider
        available_balance = user.available_balance

        if requested_amount > available_balance:
            raise serializers.ValidationError(f"Requested amount exceeds available balance (${available_balance}).")

        # Create PayoutRequest record
        payout_request = serializer.save(provider=user, amount=requested_amount, status='processing') # Start as processing
        
        # Initiate Stripe Transfer
        try:
            transfer = stripe.Transfer.create(
                amount=int(requested_amount * 100),  # Amount in cents
                currency=user.stripe_account_id.split('_')[-1].lower() if user.stripe_account_id else 'usd', # Infer currency, fallback to USD
                destination=user.stripe_account_id,
                metadata={
                    'payout_request_id': str(payout_request.id),
                    'provider_id': str(user.id)
                }
            )
            payout_request.stripe_transfer_id = transfer.id
            payout_request.status = 'processing' # Explicitly set to processing after Stripe call
            payout_request.save()
            
            # Return success response
            return Response({'message': 'Payout request submitted successfully and Stripe transfer initiated.',
                    'payout_request': PayoutRequestSerializer(payout_request).data
                }, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            # If Stripe transfer fails, mark payout request as failed
            payout_request.status = 'failed'
            payout_request.save(update_fields=['status'])
            return Response({'error': f"Stripe transfer failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Handle other potential errors
            payout_request.status = 'failed'
            payout_request.save(update_fields=['status'])
            return Response({'error': f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProviderBalanceView(generics.RetrieveAPIView):
    serializer_class = ProviderBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.request.user.role != 'provider':
            raise PermissionDenied("Only providers can view their balance.")
        return self.request.user


class AdminPayoutListView(generics.ListAPIView):
    """Admin view for all payout requests."""
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can access this

    def get_queryset(self):
        return PayoutRequest.objects.all().order_by('-created_at')


class AdminPlatformRevenueView(APIView):
    """Admin view for platform revenue overview."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, format=None):
        # Total platform earnings (sum of platform_fee from all transactions)
        total_platform_earnings = Transaction.objects.aggregate(
            total=Sum('platform_fee'))['total'] or Decimal('0.00')

        # Total payouts (sum of amount from completed payout requests)
        total_payouts = PayoutRequest.objects.filter(status='completed').aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Net revenue
        net_revenue = total_platform_earnings - total_payouts

        # Pending payouts
        pending_payouts = PayoutRequest.objects.filter(status__in=['pending', 'processing']).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')

        # Total bookings and transactions
        total_bookings = Booking.objects.count()
        total_transactions = Transaction.objects.count()

        data = {
            'total_platform_earnings': total_platform_earnings,
            'total_payouts': total_payouts,
            'net_revenue': net_revenue,
            'pending_payouts': pending_payouts,
            'total_bookings': total_bookings,
            'total_transactions': total_transactions,
        }
        serializer = PlatformRevenueSerializer(data=data)
        serializer.is_valid(raise_exception=True) # Validate the data against the serializer
        return Response(serializer.data)


class AdminTransactionListView(generics.ListAPIView):
    """Admin view for all transactions for monitoring and reconciliation."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Transaction.objects.all().order_by('-created_at')

# Hub (Agency) functionality views
class HubProjectListView(generics.ListCreateAPIView):
    serializer_class = HubProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'hub':
            return HubProject.objects.filter(hub=self.request.user)
        elif self.request.user.role == 'customer':
            return HubProject.objects.filter(customer=self.request.user)
        return HubProject.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'hub':
            return Response({"error": "Only Hubs can create projects."}, status=status.HTTP_403_FORBIDDEN)
        serializer.save(hub=self.request.user)


class HubProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = HubProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'hub':
            return HubProject.objects.filter(hub=self.request.user)
        elif self.request.user.role == 'customer':
            return HubProject.objects.filter(customer=self.request.user)
        return HubProject.objects.none()


class ProjectInviteProviderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        if request.user.role != 'hub':
            return Response({"error": "Only Hubs can invite providers to projects."}, status=status.HTTP_403_FORBIDDEN)
        
        project = get_object_or_404(HubProject, id=project_id, hub=request.user)
        provider_id = request.data.get('provider_id')
        
        if not provider_id:
            return Response({"error": "provider_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        provider = get_object_or_404(User, id=provider_id, role='provider')
        
        # Check if already a member
        if ProjectMember.objects.filter(project=project, provider=provider).exists():
            return Response({"error": "Provider is already a member of this project."}, status=status.HTTP_400_BAD_REQUEST)
        
        member = ProjectMember.objects.create(project=project, provider=provider, status='invited')
        
        # Here we would normally send an invitation email/notification
        
        return Response(ProjectMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class ProjectManageMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, project_id, member_id):
        if request.user.role != 'hub':
            return Response({"error": "Only Hubs can manage project members."}, status=status.HTTP_403_FORBIDDEN)
        
        project = get_object_or_404(HubProject, id=project_id, hub=request.user)
        member = get_object_or_404(ProjectMember, id=member_id, project=project)
        
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, project_id, member_id):
        # Allow providers to accept/reject invitations
        member = get_object_or_404(ProjectMember, id=member_id, project_id=project_id)
        
        if request.user != member.provider:
             return Response({"error": "Only the invited provider can update their status."}, status=status.HTTP_403_FORBIDDEN)
        
        new_status = request.data.get('status')
        if new_status not in ['accepted', 'rejected']:
            return Response({"error": "Invalid status. Must be 'accepted' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)
        
        member.status = new_status
        if new_status == 'accepted':
            member.joined_at = timezone.now()
        member.save()
        
        return Response(ProjectMemberSerializer(member).data)


class ProjectPackageCreateView(generics.CreateAPIView):
    serializer_class = ProjectPackageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(HubProject, id=project_id, hub=self.request.user)
        
        if self.request.user.role != 'hub':
            # This check is actually handled by HubProject.objects.get_object_or_404(...) with hub=request.user
            pass
        
        # If project already has a package, update it instead or return error
        if hasattr(project, 'package'):
             return Response({"error": "Project already has a package. Use update endpoint."}, status=status.HTTP_400_BAD_REQUEST)
             
        serializer.save(project=project)


class ProjectAvailabilityListView(generics.ListAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(HubProject, id=project_id)
        
        # Ensure the requesting user is either the hub, customer, or a member of the project
        if not (self.request.user == project.hub or \
                (project.customer and self.request.user == project.customer) or \
                project.members.filter(provider=self.request.user).exists()):
            return Response({"error": "You are not authorized to view this project's availabilities."}, status=status.HTTP_403_FORBIDDEN)

        # Return availabilities linked to any member of this project
        return Availability.objects.filter(project_member__project=project).order_by('date', 'start_time')


class ProjectMemberAvailabilityCreateView(generics.CreateAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_id')
        member_id = self.kwargs.get('member_id')
        
        project = get_object_or_404(HubProject, id=project_id, hub=self.request.user) # Only hub can create
        project_member = get_object_or_404(ProjectMember, id=member_id, project=project)

        if self.request.user.role != 'hub':
            return Response({"error": "Only Hubs can create availabilities for project members."}, status=status.HTTP_403_FORBIDDEN)

        serializer.save(provider=project_member.provider, project_member=project_member)
