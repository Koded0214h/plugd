from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.utils import timezone
from .models import User, VerificationRequest
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    CustomTokenObtainPairSerializer, UserProfileSerializer,
    ChangePasswordSerializer, VerificationRequestSerializer,
    VerificationReviewSerializer
)

class RegisterView(generics.CreateAPIView):
    """User registration view"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User created successfully'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """User login view"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Update last active
        user.last_active = timezone.now()
        user.is_online = True
        user.save(update_fields=['last_active', 'is_online'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login successful'
        })


class LogoutView(APIView):
    """User logout view"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Update user status
            request.user.is_online = False
            request.user.save(update_fields=['is_online'])
            
            # Blacklist the refresh token
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logout(request)
            return Response({'message': 'Logout successful'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view"""
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """View and update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': ['Wrong password.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password updated successfully'})


class VerificationRequestView(generics.CreateAPIView):
    """Submit verification request"""
    serializer_class = VerificationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VerificationStatusView(APIView):
    """Check verification status"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        latest_request = user.verification_requests.first()
        
        return Response({
            'status': user.verification_status,
            'submitted_at': user.verification_submitted_at,
            'reviewed_at': user.verification_reviewed_at,
            'rejection_reason': user.verification_rejection_reason,
            'has_pending_request': latest_request and latest_request.status == 'pending' if latest_request else False
        })


# Admin Views
class AdminVerificationQueueView(generics.ListAPIView):
    """Admin view for verification queue"""
    serializer_class = VerificationRequestSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return VerificationRequest.objects.filter(status='pending').order_by('created_at')


class AdminVerificationReviewView(APIView):
    """Admin review verification request"""
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request, request_id):
        try:
            verification_request = VerificationRequest.objects.get(id=request_id, status='pending')
        except VerificationRequest.DoesNotExist:
            return Response(
                {'error': 'Verification request not found or already processed'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        status_choice = serializer.validated_data['status']
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        
        # Update verification request
        verification_request.status = status_choice
        verification_request.reviewed_by = request.user
        verification_request.reviewed_at = timezone.now()
        
        if status_choice == 'rejected':
            verification_request.rejection_reason = rejection_reason
        
        verification_request.save()
        
        # Update user verification status
        user = verification_request.user
        if status_choice == 'verified':
            user.verify_user()
        else:
            user.reject_verification(rejection_reason)
        
        return Response({
            'message': f'Verification {status_choice} successfully',
            'user': UserProfileSerializer(user).data
        })