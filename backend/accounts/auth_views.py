"""Authentication endpoints for MarketPulse.

These endpoints are separated from accounts/views.py so profile-related
functionality in that file can remain untouched.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model, login as django_login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .email_utils import (
    EMAIL_VERIFICATION_SALT,
    send_password_reset_email,
    send_verification_email,
)
from .session_security import start_user_session
from .models import UserProfile
from .serializers import RegistrationSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginRateThrottle(AnonRateThrottle):
    scope = "auth_login"


class VerificationRateThrottle(AnonRateThrottle):
    scope = "auth_verification"


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "auth_password_reset"


def _verification_is_required():
    """Never allow the development bypass when DEBUG is False."""
    return not (settings.DEBUG and not settings.EMAIL_VERIFICATION_REQUIRED)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"email_verified": False},
    )

    # Local development convenience. Production always requires verification.
    if not _verification_is_required():
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])

        return Response(
            {
                "message": (
                    "Account created successfully. Email verification is "
                    "disabled in local development. You can now log in."
                ),
                "email": user.email,
                "email_sent": False,
                "email_verified": True,
            },
            status=status.HTTP_201_CREATED,
        )

    try:
        send_verification_email(user)
    except Exception:
        logger.exception("Unable to send verification email for user %s", user.pk)
        return Response(
            {
                "message": (
                    "Your account was created, but the verification email "
                    "could not be sent. Please request another email."
                ),
                "email": user.email,
                "email_sent": False,
                "email_verified": False,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "message": "Account created. Please verify your email before logging in.",
            "email": user.email,
            "email_sent": True,
            "email_verified": False,
        },
        status=status.HTTP_201_CREATED,
    )


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    email = str(request.data.get("email", "")).strip()
    password = request.data.get("password", "")

    if not email or not isinstance(password, str) or not password:
        return Response(
            {"detail": "Email address and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(email__iexact=email).first()
    if user is None or not user.is_active or not user.check_password(password):
        return Response(
            {"detail": "Invalid email address or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        # Legacy users without a profile are treated as verified. New
        # registrations explicitly create their profile as unverified.
        defaults={"email_verified": True},
    )

    if not _verification_is_required():
        # Make local development friction-free for existing test accounts too.
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])
    elif not profile.email_verified:
        return Response(
            {
                "detail": "Please verify your email address before logging in.",
                "email_verification_required": True,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    django_login(request._request, user)
    start_user_session(request._request)

    return Response(
        {
            "message": "Login successful.",
            "user": {
                "id": user.pk,
                "username": user.get_username(),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([VerificationRateThrottle])
def verify_email(request):
    token = request.data.get("token", "")
    if not isinstance(token, str) or not token:
        return Response(
            {"detail": "Verification token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = signing.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_MAX_AGE,
        )
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("email"), str)
            or "user_id" not in payload
        ):
            raise ValueError("Invalid verification payload")

        user = User.objects.get(
            pk=payload["user_id"],
            email__iexact=payload["email"],
            is_active=True,
        )
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError, ValueError):
        return Response(
            {"detail": "This verification link is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"email_verified": False},
    )
    if profile.email_verified:
        return Response({"message": "Your email is already verified."})

    profile.email_verified = True
    profile.save(update_fields=["email_verified"])
    return Response({"message": "Your email has been verified. You can now log in."})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([VerificationRateThrottle])
def resend_verification_email(request):
    email = str(request.data.get("email", "")).strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first()

    if user:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"email_verified": True},
        )

        if not _verification_is_required():
            if not profile.email_verified:
                profile.email_verified = True
                profile.save(update_fields=["email_verified"])
        elif not profile.email_verified:
            try:
                send_verification_email(user)
            except Exception:
                logger.exception("Unable to resend verification email for user %s", user.pk)

    # Do not reveal whether an account exists.
    return Response(
        {
            "message": (
                "If an unverified account exists for that email, "
                "a verification email will be sent."
            )
        }
    )



@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRateThrottle])
def request_password_reset(request):
    email = str(request.data.get("email", "")).strip().lower()

    user = User.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()

    reset_url = None

    if user:
        try:
            reset_url = send_password_reset_email(user)

        except Exception:
            logger.exception(
                "Unable to send password reset email for user %s",
                user.pk,
            )

    response_data = {
        "message": (
            "If an account exists for that email, "
            "a password reset link will be sent."
        )
    }

    # Only expose the link in local development.
    if (
        settings.DEBUG
        and not settings.EMAIL_VERIFICATION_REQUIRED
        and reset_url
    ):
        response_data["dev_reset_url"] = reset_url

    return Response(response_data, status=status.HTTP_200_OK)



@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRateThrottle])
def confirm_password_reset(request):
    uidb64 = request.data.get("uid")
    token = request.data.get("token")
    password = request.data.get("password")
    password_confirm = request.data.get("password_confirm")

    values = (uidb64, token, password, password_confirm)
    if not all(values) or not all(isinstance(value, str) for value in values):
        return Response(
            {"detail": "All password reset fields are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != password_confirm:
        return Response(
            {"password_confirm": "The passwords do not match."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {"detail": "This password reset link is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(user, token):
        return Response(
            {"detail": "This password reset link is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        return Response(
            {"password": list(exc.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save(update_fields=["password"])
    return Response({"message": "Your password has been reset successfully."})
