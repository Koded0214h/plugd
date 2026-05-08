from rest_framework import generics, serializers, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
import stripe
import cloudinary.uploader

from .models import ProviderProfile, User, VerificationRequest, UserRole, VerificationStatus # Import UserRole and VerificationStatus
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    AdminRegisterSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    VerificationRequestSerializer,
    AdminVerificationReviewSerializer,
    ProviderProfileSerializer,
    AdminUserListSerializer,  # Import the new serializer
    GoogleAuthSerializer,
    ForgotPasswordRequestSerializer,
    ResetPasswordSerializer,
)
from core.permissions import IsAdmin, IsCustomer, IsProvider, IsHub
from .services import send_onboarding_email, build_password_reset_link, send_password_reset_email


# Configure Stripe (moved to settings.py, but good to ensure it's available)
stripe.api_key = settings.STRIPE_SECRET_KEY


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class AdminRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminRegisterSerializer

    def get_permissions(self):
        # Allow unauthenticated access only when bootstrapping the first admin
        if not User.objects.filter(role=UserRole.ADMIN).exists():
            return [permissions.AllowAny()]
        return [IsAdmin()]


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                return Response({'detail': 'User account is inactive.'}, status=status.HTTP_401_UNAUTHORIZED)
            
            serializer = self.get_serializer(data=request.data)
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                return Response({'detail': e.args[0]}, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = build_password_reset_link(uidb64, token)
            send_password_reset_email(user, reset_link)

        return Response(
            {'detail': 'If an account with that email exists, a password reset link has been sent.'},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UnicodeDecodeError, User.DoesNotExist):
            return Response(
                {'detail': 'Invalid or expired password reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Invalid or expired password reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])

        return Response(
            {'detail': 'Password reset successfully.'},
            status=status.HTTP_200_OK,
        )


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            return Response(
                {'detail': 'Google OAuth is not configured on the server.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.auth import exceptions as google_auth_exceptions
            from google.oauth2 import id_token as google_id_token
        except ImportError:
            return Response(
                {'detail': 'google-auth is not installed on the server.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            payload = google_id_token.verify_oauth2_token(
                serializer.validated_data['id_token'],
                GoogleAuthRequest(),
                settings.GOOGLE_OAUTH_CLIENT_ID,
            )
        except (ValueError, google_auth_exceptions.GoogleAuthError):
            return Response(
                {'detail': 'Invalid Google token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payload.get('email') or not payload.get('email_verified'):
            return Response(
                {'detail': 'Google account email is not verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = payload['email'].strip().lower()
        first_name = (payload.get('given_name') or '').strip()
        last_name = (payload.get('family_name') or '').strip()
        role = serializer.validated_data.get('role', UserRole.CUSTOMER)
        if role == UserRole.ADMIN:
            return Response(
                {'detail': 'Cannot authenticate as admin via Google OAuth.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        created = False

        if user is None:
            user = User.objects.create(
                email=email,
                username=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])
            created = True
        else:
            updated_fields = []
            if first_name and not user.first_name:
                user.first_name = first_name
                updated_fields.append('first_name')
            if last_name and not user.last_name:
                user.last_name = last_name
                updated_fields.append('last_name')
            if not user.is_active:
                user.is_active = True
                updated_fields.append('is_active')
            if updated_fields:
                user.save(update_fields=updated_fields)

        if created:
            send_onboarding_email(user, source="google")

        refresh = RefreshToken.for_user(user)
        user_data = UserProfileSerializer(user).data

        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data,
                'is_new_user': created,
            },
            status=status.HTTP_200_OK,
        )


class AdminLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            email = request.data.get('email')
            try:
                user = User.objects.get(email=email)
                if user.role != UserRole.ADMIN:
                    return Response({'detail': 'Access denied. Admin account required.'}, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                pass
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    def perform_update(self, serializer):
        # Handle avatar update separately if a file is provided
        avatar_file = self.request.data.get('avatar')
        if avatar_file:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(avatar_file)
            serializer.validated_data['avatar'] = upload_result['secure_url']
        elif avatar_file is False: # If frontend explicitly sends avatar: null or empty
            serializer.validated_data['avatar'] = None # Clear the avatar
        
        serializer.save()


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data.get('old_password')):
                return Response({'old_password': ['Wrong password.']}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data.get('new_password'))
            user.save()
            return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerificationRequestView(generics.CreateAPIView):
    queryset = VerificationRequest.objects.all()
    serializer_class = VerificationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if VerificationRequest.objects.filter(user=self.request.user, status=VerificationStatus.PENDING).exists():
            raise serializers.ValidationError("A pending verification request already exists for this user.")

        verification_doc_file = self.request.data.get('document')
        if not verification_doc_file:
            raise serializers.ValidationError("Verification document is required.")

        try:
            upload_result = cloudinary.uploader.upload(verification_doc_file)
        except Exception as e:
            raise serializers.ValidationError(f"Document upload failed: {str(e)}")

        serializer.save(
            user=self.request.user,
            status=VerificationStatus.PENDING,
            document=upload_result['secure_url'],
        )
        self.request.user.submit_for_verification()


class VerificationStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({'verification_status': user.verification_status}, status=status.HTTP_200_OK)


class AdminVerificationQueueView(generics.ListAPIView):
    queryset = VerificationRequest.objects.filter(status=VerificationStatus.PENDING).order_by('-created_at')
    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAdmin]


class AdminVerificationReviewView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, request_id):
        verification_request = get_object_or_404(VerificationRequest, id=request_id)
        user_to_verify = verification_request.user

        serializer = AdminVerificationReviewSerializer(data=request.data)
        if serializer.is_valid():
            action_status = serializer.validated_data['status']
            rejection_reason = serializer.validated_data.get('rejection_reason', '')

            if action_status == 'verified':
                user_to_verify.verify_user()
                verification_request.status = VerificationStatus.VERIFIED
                verification_request.reviewed_by = request.user
                verification_request.reviewed_at = timezone.now()
                verification_request.rejection_reason = ""
                verification_request.save()
                return Response({'message': f'User {user_to_verify.email} verified successfully.'})
            elif action_status == 'rejected':
                if not rejection_reason:
                    return Response({'rejection_reason': 'Rejection reason is required.'}, status=status.HTTP_400_BAD_REQUEST)
                user_to_verify.reject_verification(rejection_reason)
                verification_request.status = VerificationStatus.REJECTED
                verification_request.reviewed_by = request.user
                verification_request.reviewed_at = timezone.now()
                verification_request.rejection_reason = rejection_reason
                verification_request.save()
                return Response({'message': f'User {user_to_verify.email} verification rejected.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProviderOwnProfileView(generics.RetrieveUpdateAPIView):
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer
    permission_classes = [IsProvider]

    def get_object(self):
        user = self.request.user
        # Ensure a ProviderProfile exists for the provider
        profile, created = ProviderProfile.objects.get_or_create(user=user)
        return profile
    
    def perform_update(self, serializer):
        business_logo_file = self.request.data.get('business_logo')
        if business_logo_file:
            upload_result = cloudinary.uploader.upload(business_logo_file)
            serializer.validated_data['business_logo'] = upload_result['secure_url']
        elif business_logo_file is False:
            serializer.validated_data['business_logo'] = None

        serializer.save()


class PublicProviderProfileView(generics.RetrieveAPIView):
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    lookup_field = 'user_id'

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id, role=UserRole.PROVIDER, is_active=True)
        return get_object_or_404(ProviderProfile, user=user)


class CreateStripeConnectAccountView(APIView):
    """
    Creates a Stripe Connect account for the provider and returns an onboarding link.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'provider':
            return Response({'error': 'Only providers can create Stripe accounts.'}, status=403)

        # If user already has a stripe account id and onboarding is complete, return dashboard link
        if user.stripe_account_id and user.stripe_onboarding_complete:
            # Generate a link to the Stripe Express dashboard
            account_link = stripe.AccountLink.create(
                account=user.stripe_account_id,
                refresh_url=f"{settings.FRONTEND_URL}/stripe/refresh",
                return_url=f"{settings.FRONTEND_URL}/stripe/return",
                type='account_onboarding',
            )
            return Response({'url': account_link.url})

        # Create a new Stripe account (Express type for easier onboarding)
        try:
            account = stripe.Account.create(
                type='express',
                country='GB',  # adjust based on your market
                email=user.email,
                business_type='individual',  # or 'company'
                individual={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                },
                metadata={'user_id': str(user.id)}
            )
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=400)

        # Save the account ID
        user.stripe_account_id = account.id
        user.stripe_onboarding_complete = False
        user.save()

        # Create an account link for onboarding
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"{settings.FRONTEND_URL}/stripe/refresh",
            return_url=f"{settings.FRONTEND_URL}/stripe/return",
            type='account_onboarding',
        )

        return Response({'url': account_link.url})


class StripeOnboardingRefreshView(APIView):
    """If the user exits onboarding, they come here to get a new link."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Redirect to the account creation view again (which will generate a new link)
        return Response({'message': 'Redirect to create account endpoint'})


class StripeReturnView(APIView):
    """
    Called after provider completes Stripe onboarding and lands on /stripe/return.
    Checks Stripe account status and updates stripe_onboarding_complete.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'provider':
            return Response({'error': 'Only providers can complete Stripe onboarding.'}, status=status.HTTP_403_FORBIDDEN)

        if not user.stripe_account_id:
            return Response({'stripe_onboarding_complete': False, 'charges_enabled': False, 'payouts_enabled': False})

        try:
            account = stripe.Account.retrieve(user.stripe_account_id)
            onboarding_complete = bool(account.charges_enabled and account.payouts_enabled)
            if onboarding_complete and not user.stripe_onboarding_complete:
                user.stripe_onboarding_complete = True
                user.save(update_fields=['stripe_onboarding_complete'])
            return Response({
                'stripe_onboarding_complete': user.stripe_onboarding_complete,
                'charges_enabled': account.charges_enabled,
                'payouts_enabled': account.payouts_enabled,
            })
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)





class AdminUserUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        is_active = request.data.get('is_active')
        if is_active is None or not isinstance(is_active, bool):
            return Response({'is_active': 'This field is required and must be a boolean.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = is_active
        user.save(update_fields=['is_active'])
        action = 'reinstated' if is_active else 'suspended'
        return Response({'detail': f'User {user.email} has been {action}.'}, status=status.HTTP_200_OK)


class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')

        role = self.request.query_params.get('role', None)
        status = self.request.query_params.get('status', None)
        is_active = self.request.query_params.get('is_active', None)

        if role:
            # Validate role to be one of the choices in UserRole
            if role not in [r.value for r in UserRole]:
                return User.objects.none() # Return empty queryset if role is invalid
            queryset = queryset.filter(role=role)
        
        if status:
            # Validate status to be one of the choices in VerificationStatus
            if status not in [s.value for s in VerificationStatus]:
                return User.objects.none() # Return empty queryset if status is invalid
            queryset = queryset.filter(verification_status=status)

        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        return queryset
