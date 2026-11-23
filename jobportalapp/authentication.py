from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserMaster


class UserMasterJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that authenticates against UserMaster.
    """
    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')
        if not user_id:
            raise InvalidToken("Token contained no recognizable user identification.")

        try:
            user = UserMaster.objects.get(id=user_id)
        except UserMaster.DoesNotExist:
            raise AuthenticationFailed("User not found.", code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed("User account is inactive.", code="user_inactive")

        return user


def get_tokens_for_user(user):
    """
    Generate access and refresh JWT tokens for a UserMaster instance.
    """
    refresh = RefreshToken()
    refresh['user_id'] = user.id
    refresh['email']   = user.email
    refresh['role']    = user.role

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# ── Custom Role-based Permissions ─────────────────────────────────────────────

class IsCandidateUser(permissions.BasePermission):
    """Allows access only to authenticated candidate users."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == 'Candidate'
        )


class IsCompanyUser(permissions.BasePermission):
    """Allows access only to authenticated company users."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == 'Company'
        )


class IsAdminRoleUser(permissions.BasePermission):
    """Allows access only to admin role users."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == 'Admin'
        )

