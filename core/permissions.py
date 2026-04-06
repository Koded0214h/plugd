from rest_framework import permissions
from users.models import UserRole # Assuming UserRole is defined in users.models

class IsAdmin(permissions.BasePermission):
    """Allows access only to admin users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsCustomer(permissions.BasePermission):
    """Allows access only to customer users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.CUSTOMER


class IsProvider(permissions.BasePermission):
    """Allows access only to service provider users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.PROVIDER


class IsHub(permissions.BasePermission):
    """Allows access only to hub users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.HUB
