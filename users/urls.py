from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('auth/register/', views.RegisterView.as_view(), name='auth_register'),
    path('auth/login/', views.LoginView.as_view(), name='auth_login'),
    path('auth/admin/register/', views.AdminRegisterView.as_view(), name='auth_admin_register'),
    path('auth/admin/login/', views.AdminLoginView.as_view(), name='auth_admin_login'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth_logout'),
    path('auth/token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Verification
    path('verification/request/', views.VerificationRequestView.as_view(), name='verification_request'),
    path('verification/status/', views.VerificationStatusView.as_view(), name='verification_status'),
    
    # Admin
    path('admin/verification/queue/', views.AdminVerificationQueueView.as_view(), name='admin_verification_queue'),
    path('admin/verification/review/<uuid:request_id>/', views.AdminVerificationReviewView.as_view(), name='admin_verification_review'),

    # Provider Endpoint
    path('provider/profile/', views.ProviderOwnProfileView.as_view(), name='provider-profile-own'), 
    path('provider/profile/<uuid:user_id>/', views.PublicProviderProfileView.as_view(), name='provider-profile-public'),    

    path('stripe/create-account/', views.CreateStripeConnectAccountView.as_view(), name='stripe-create-account'),
    path('stripe/refresh/', views.StripeOnboardingRefreshView.as_view(), name='stripe-refresh'),
    path('stripe/return/', views.StripeOnboardingReturnView.as_view(), name='stripe-return'),
]


