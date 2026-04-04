from django.urls import path
from . import views

urlpatterns = [
    # Provider availability
    path('availabilities/', views.AvailabilityListCreateView.as_view(), name='availability-list'),
    path('availabilities/<uuid:pk>/', views.AvailabilityDetailView.as_view(), name='availability-detail'),

    # Public available slots for a listing
    path('listings/<uuid:listing_id>/slots/', views.ListingAvailableSlotsView.as_view(), name='listing-slots'),

    # Booking creation and management
    path('bookings/', views.UserBookingListView.as_view(), name='user-bookings'),
    path('bookings/create/', views.BookingCreateView.as_view(), name='booking-create'),
    path('bookings/<uuid:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),

    # Stripe webhook
    path('stripe-webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    path('payouts/', views.ProviderPayoutRequestView.as_view(), name='provider-payout-request'),
    path('admin/payouts/', views.AdminPayoutListView.as_view(), name='admin-payout-list'),
]