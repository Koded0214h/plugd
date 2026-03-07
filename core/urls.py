from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),

    # Provider listing management
    path('listings/', views.ProviderListingListCreateView.as_view(), name='provider-listing-list'),
    path('listings/<uuid:pk>/', views.ProviderListingRetrieveUpdateDestroyView.as_view(), name='provider-listing-detail'),

    # Public listings
    path('public/listings/', views.PublicListingListView.as_view(), name='public-listing-list'),
    path('public/listings/<uuid:pk>/', views.PublicListingDetailView.as_view(), name='public-listing-detail'),
]