from rest_framework import generics, permissions, filters
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from .models import ServiceListing, ServiceCategory
from .serializers import (
    ServiceListingSerializer, 
    ServiceListingCreateUpdateSerializer,
    ServiceCategorySerializer
)

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