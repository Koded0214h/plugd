from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User, UserRole
from core.models import ServiceCategory, ServiceListing, ServiceRequest, Quote
from bookings.models import Booking
from decimal import Decimal
import json

class AdminAuthTests(APITestCase):
    # ... (existing AdminAuthTests code) ...
    pass # Placeholder to show this is not the file being modified

class RequestQuoteBookingTests(APITestCase):
    def setUp(self):
        # Users
        self.customer = User.objects.create_user(email='customer@example.com', password='password', role=UserRole.CUSTOMER)
        self.provider = User.objects.create_user(email='provider@example.com', password='password', role=UserRole.PROVIDER, stripe_account_id='acct_12345', stripe_onboarding_complete=True)
        self.provider.save()
        self.admin = User.objects.create_user(email='admin@example.com', password='password', role=UserRole.ADMIN, is_staff=True)
        self.admin.save()

        # Service Category
        self.category = ServiceCategory.objects.create(name='Photography', is_active=True)

        # Service Listing
        self.listing = ServiceListing.objects.create(
            provider=self.provider,
            category=self.category,
            title='Wedding Photography Package',
            description='Full day wedding photography.',
            pricing_type='fixed',
            price=Decimal('1500.00'),
            currency='USD',
            is_remote_available=False,
            is_active=True
        )

        # Service Request
        self.service_request = ServiceRequest.objects.create(
            customer=self.customer,
            category=self.category,
            title='Wedding Photoshoot',
            description='Need a photographer for my wedding.',
            budget=Decimal('1500.00'),
            location='Los Angeles, CA',
            preferred_date='2026-04-15',
            preferred_time='10:00:00',
            status='open'
        )

        # Quote
        self.quote = Quote.objects.create(
            service_request=self.service_request,
            provider=self.provider,
            description='Professional wedding photography for your special day.',
            price=Decimal('1450.00'),
            estimated_duration='8 hours',
            status='pending',
            valid_until=timezone.now() + timedelta(days=7)
        )

        # URLs
        self.quote_accept_url = reverse('quote-accept', kwargs={'pk': self.quote.id})
        self.service_request_detail_url = reverse('service-request-detail', kwargs={'pk': self.service_request.id})

    def test_customer_accepts_quote_creates_booking(self):
        """Test that a customer accepting a quote creates a booking and initiates payment."""
        self.client.force_login(self.customer)
        
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check response data
        self.assertIn('message', response.data)
        self.assertIn('booking', response.data)
        self.assertEqual(response.data['message'], 'Quote accepted successfully. Booking created and payment initiated.')
        
        booking_data = response.data['booking']
        self.assertIn('id', booking_data)
        self.assertIn('stripe_payment_intent_id', booking_data)
        self.assertIn('stripe_client_secret', booking_data)
        self.assertEqual(booking_data['total_amount'], str(self.quote.price))
        self.assertEqual(booking_data['status'], 'pending')
        self.assertEqual(booking_data['date'], str(self.service_request.preferred_date))
        self.assertEqual(booking_data['start_time'], str(self.service_request.preferred_time))
        # Check end_time calculation (8 hours from 10:00:00 is 18:00:00)
        self.assertEqual(booking_data['end_time'], '18:00:00') 

        # Check database state
        updated_quote = Quote.objects.get(id=self.quote.id)
        self.assertEqual(updated_quote.status, 'accepted')

        updated_request = ServiceRequest.objects.get(id=self.service_request.id)
        self.assertEqual(updated_request.status, 'accepted')

        booking = Booking.objects.filter(
            customer=self.customer,
            provider=self.provider,
            listing=self.listing,
            date=self.service_request.preferred_date,
            start_time=self.service_request.preferred_time,
            end_time='18:00:00', # Calculated end time
            total_amount=self.quote.price,
            status='pending'
        ).first()
        self.assertIsNotNone(booking)
        self.assertIsNotNone(booking.stripe_payment_intent_id)
        self.assertIsNotNone(booking.stripe_client_secret)

    def test_customer_cannot_accept_quote_for_other_request(self):
        """Test that a customer can only accept quotes for their own requests."""
        self.client.force_login(self.customer)
        
        # Create another customer and their request
        other_customer = User.objects.create_user(email='other@example.com', password='password', role=UserRole.CUSTOMER)
        other_request = ServiceRequest.objects.create(
            customer=other_customer,
            category=self.category,
            title='Another Photoshoot',
            description='Need photos for another event.',
            budget=Decimal('1000.00'),
            preferred_date='2026-05-01',
            preferred_time='14:00:00',
            status='open'
        )
        # Create a quote for this other request (from the same provider)
        other_quote = Quote.objects.create(
            service_request=other_request,
            provider=self.provider,
            description='Quote for other event.',
            price=Decimal('950.00'),
            estimated_duration='6 hours',
            status='pending',
        )
        
        response = self.client.post(reverse('quote-accept', kwargs={'pk': other_quote.id}), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('You can only accept quotes for your own service requests.', response.data['error'])

    def test_provider_cannot_accept_quote(self):
        """Test that a provider cannot accept a quote."""
        self.client.force_login(self.provider)
        
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('You can only accept quotes for your own service requests.', response.data['error'])

    def test_accept_quote_updates_statuses(self):
        """Test that accepting a quote correctly updates quote and request statuses."""
        self.client.force_login(self.customer)
        
        self.client.post(self.quote_accept_url, format='json')
        
        updated_quote = Quote.objects.get(id=self.quote.id)
        self.assertEqual(updated_quote.status, 'accepted')
        
        updated_request = ServiceRequest.objects.get(id=self.service_request.id)
        self.assertEqual(updated_request.status, 'accepted')

    def test_accept_quote_only_once(self):
        """Test that a quote can only be accepted once."""
        self.client.force_login(self.customer)
        
        # Accept first time
        response1 = self.client.post(self.quote_accept_url, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Try to accept again
        response2 = self.client.post(self.quote_accept_url, format='json')
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND) # Should be not found or not pending
        self.assertIn('error', response2.data)
        self.assertIn('Quote not found or not in pending status.', response2.data['error'])

    def test_accept_quote_for_non_open_request(self):
        """Test that a quote cannot be accepted if the request is not open or in_discussion."""
        self.service_request.status = 'closed'
        self.service_request.save()
        
        self.client.force_login(self.customer)
        
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('This service request is no longer open for quote acceptance.', response.data['error'])

    def test_booking_creation_with_stripe_details(self):
        """Test that the created booking has correct Stripe PaymentIntent details."""
        self.client.force_login(self.customer)
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking_data = response.data['booking']
        
        self.assertIsNotNone(booking_data['stripe_payment_intent_id'])
        self.assertIsNotNone(booking_data['stripe_client_secret'])
        self.assertEqual(booking_data['status'], 'pending')

    def test_booking_creation_with_correct_pricing_and_duration(self):
        """Test that the created booking has correct pricing and calculated end time."""
        self.client.force_login(self.customer)
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking_data = response.data['booking']
        
        # Check pricing
        self.assertEqual(booking_data['total_amount'], str(self.quote.price))
        
        # Check calculated end time (8 hours from 10:00:00 is 18:00:00)
        self.assertEqual(booking_data['start_time'], '10:00:00')
        self.assertEqual(booking_data['end_time'], '18:00:00')

    def test_booking_creation_with_correct_service_listing_and_provider(self):
        """Test that the created booking correctly links to the provider and service listing."""
        self.client.force_login(self.customer)
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking_id = response.data['booking']['id']
        
        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.provider, self.provider)
        self.assertEqual(booking.listing, self.listing)
        self.assertEqual(booking.customer, self.customer)

    def test_booking_creation_fails_if_provider_stripe_not_complete(self):
        """Test booking creation fails if provider Stripe onboarding is not complete."""
        self.provider.stripe_onboarding_complete = False
        self.provider.save()
        
        self.client.force_login(self.customer)
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Provider is not ready to receive payments.', response.data['error'])

    def test_booking_creation_fails_if_no_active_listing_for_category(self):
        """Test booking creation fails if no active listing is found for provider/category."""
        # Make the provider's listing inactive
        self.listing.is_active = False
        self.listing.save()
        
        self.client.force_login(self.customer)
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('No active service listing found for this provider and category.', response.data['error'])

    def test_booking_creation_fails_if_no_preferred_date_or_time(self):
        """Test booking creation fails if preferred date/time are missing from ServiceRequest."""
        self.service_request.preferred_date = None
        self.service_request.preferred_time = None
        self.service_request.save()
        
        self.client.force_login(self.customer)
        response = self.client.post(self.quote_accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Preferred date and time must be provided', response.data['error'])

    def test_quote_rejection(self):
        """Test that a provider can reject a quote."""
        self.client.force_login(self.provider)
        
        response = self.client.post(reverse('quote-reject', kwargs={'pk': self.quote.id}), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Quote rejected successfully.')
        
        updated_quote = Quote.objects.get(id=self.quote.id)
        self.assertEqual(updated_quote.status, 'rejected')

    def test_provider_cannot_reject_other_provider_quote(self):
        """Test that a provider can only reject their own quotes."""
        # Create another provider and their quote
        other_provider = User.objects.create_user(email='otherprovider@example.com', password='password', role=UserRole.PROVIDER, stripe_account_id='acct_67890', stripe_onboarding_complete=True)
        other_quote = Quote.objects.create(
            service_request=self.service_request,
            provider=other_provider,
            description='Another quote.',
            price=Decimal('1300.00'),
            estimated_duration='7 hours',
            status='pending'
        )
        
        self.client.force_login(self.provider) # Logged in as the first provider
        
        response = self.client.post(reverse('quote-reject', kwargs={'pk': other_quote.id}), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('You can only reject your own quotes.', response.data['error'])

    def test_customer_cannot_reject_quote(self):
        """Test that a customer cannot reject a quote."""
        self.client.force_login(self.customer)
        
        response = self.client.post(reverse('quote-reject', kwargs={'pk': self.quote.id}), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('You can only reject your own quotes.', response.data['error'])
