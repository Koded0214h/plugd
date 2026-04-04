from django.urls import path
from . import views

urlpatterns = [
    # Provider coupons
    path('provider/coupons/', views.ProviderCouponListCreateView.as_view(), name='provider-coupon-list'),
    path('provider/coupons/<uuid:pk>/', views.ProviderCouponDetailView.as_view(), name='provider-coupon-detail'),

    # Admin coupons
    path('admin/coupons/', views.AdminCouponListCreateView.as_view(), name='admin-coupon-list'),
    path('admin/coupons/<uuid:pk>/', views.AdminCouponDetailView.as_view(), name='admin-coupon-detail'),

    # Apply coupon (public, authenticated)
    path('apply/', views.CouponApplyView.as_view(), name='coupon-apply'),
]