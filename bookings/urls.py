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
    path('bookings/<uuid:pk>/approve/', views.BookingApproveView.as_view(), name='booking-approve'),
    path('bookings/<uuid:pk>/reject/', views.BookingRejectView.as_view(), name='booking-reject'),

    # Stripe webhook
    path('stripe-webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    path('payouts/', views.ProviderPayoutRequestView.as_view(), name='provider-payout-request'),
    path('payouts/balance/', views.ProviderBalanceView.as_view(), name='provider-balance'),
    path('admin/payouts/', views.AdminPayoutListView.as_view(), name='admin-payout-list'),
    path('admin/payouts/queue/', views.AdminPayoutQueueView.as_view(), name='admin-payout-queue'),
    path('admin/revenue/', views.AdminPlatformRevenueView.as_view(), name='admin-platform-revenue'),
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin-transaction-list'),

    # Hub Projects
    path('projects/', views.HubProjectListView.as_view(), name='hub-project-list'),
    path('projects/<uuid:pk>/', views.HubProjectDetailView.as_view(), name='hub-project-detail'),
    path('projects/<uuid:project_id>/invite/', views.ProjectInviteProviderView.as_view(), name='project-invite-provider'),
    path('projects/<uuid:project_id>/members/<uuid:member_id>/', views.ProjectManageMemberView.as_view(), name='project-manage-member'),
    path('projects/<uuid:project_id>/package/', views.ProjectPackageCreateView.as_view(), name='project-package-create'),

    # Project Availabilities
    path('projects/<uuid:project_id>/availabilities/', views.ProjectAvailabilityListView.as_view(), name='project-availability-list'),
    path('projects/<uuid:project_id>/members/<uuid:member_id>/availabilities/', views.ProjectMemberAvailabilityCreateView.as_view(), name='project-member-availability-create'),
]