from django.urls import path
from . import views

urlpatterns = [
    # Category views
    path('categories/', views.CategoryListView.as_view(), name='category-list'),

    # Listing views (Provider & Public)
    path('listings/', views.ProviderListingListCreateView.as_view(), name='provider-listing-list'),
    path('listings/<uuid:pk>/', views.ProviderListingRetrieveUpdateDestroyView.as_view(), name='provider-listing-detail'),
    path('public/listings/', views.PublicListingListView.as_view(), name='public-listing-list'),
    path('public/listings/<uuid:pk>/', views.PublicListingDetailView.as_view(), name='public-listing-detail'),

    # Service Request views (Customer & Provider)
    path('requests/', views.ServiceRequestListView.as_view(), name='service-request-list'),
    path('requests/<uuid:pk>/', views.ServiceRequestDetailView.as_view(), name='service-request-detail'),
    path('requests/<uuid:pk>/update-status/', views.ServiceRequestUpdateStatusView.as_view(), name='service-request-update-status'),

    # Quote views (Provider & Customer)
    path('requests/<uuid:service_request_id>/quotes/', views.QuoteListCreateView.as_view(), name='quote-list-create'),
    path('quotes/<uuid:pk>/', views.QuoteDetailView.as_view(), name='quote-detail'),
    path('quotes/<uuid:pk>/accept/', views.QuoteAcceptView.as_view(), name='quote-accept'),
    path('quotes/<uuid:pk>/reject/', views.QuoteRejectView.as_view(), name='quote-reject'),

    # Review views
    path('reviews/create/', views.CustomerReviewCreateView.as_view(), name='review-create'),
    path('provider/reviews/', views.ProviderReviewListView.as_view(), name='provider-review-list'),
]
