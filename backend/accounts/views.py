
import logging

from pathlib import Path

from django.conf import settings
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.tokens import default_token_generator
from django.middleware.csrf import get_token
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes,
    throttle_classes,
)
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .session_security import (extend_user_activity, session_status)
from .email_utils import (
    EMAIL_VERIFICATION_SALT,
    send_verification_email,
    send_password_reset_email,
)
from .models import UserProfile
from .serializers import RegistrationSerializer, UserSerializer


logger = logging.getLogger(__name__)
User = get_user_model()


# --------------------------------------------------
# Authentication rate limiting
# --------------------------------------------------

class VerificationRateThrottle(AnonRateThrottle):
    scope = "auth_verification"


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "auth_password_reset"


# --------------------------------------------------
# CSRF
# --------------------------------------------------

@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request):
    return Response({"csrfToken": get_token(request)})


# --------------------------------------------------
# Registration
# --------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.save()

    # Development-only shortcut: automatically verify local test accounts.
    if settings.DEBUG and not settings.EMAIL_VERIFICATION_REQUIRED:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"email_verified": True},
        )

        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])

        return Response(
            {
                "message": (
                    "Account created successfully. "
                    "Email verification is skipped in development mode."
                ),
                "email": user.email,
                "email_sent": False,
                "email_verified": True,
            },
            status=status.HTTP_201_CREATED,
        )

    # Normal verification flow for staging and production.
    try:
        send_verification_email(user)

    except Exception:
        logger.exception("Unable to send verification email.")

        return Response(
            {
                "message": (
                    "Your account was created, but we could not send "
                    "the verification email. Please request another email."
                ),
                "email": user.email,
                "email_sent": False,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "message": (
                "Account created. Please verify your email before logging in."
            ),
            "email": user.email,
            "email_sent": True,
        },
        status=status.HTTP_201_CREATED,
    )



# --------------------------------------------------
# Login
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = request.data.get("password", "")

    if not email or not isinstance(password, str) or not password:
        return Response(
            {"detail": "Email and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_by_email = User.objects.filter(
            email__iexact=email
        ).first()

        username = user_by_email.username if user_by_email else email

        user = authenticate(
            request,
            username=username,
            password=password,
        )

    except Exception:
        logger.exception("Authentication failed unexpectedly.")

        return Response(
            {"detail": "Unable to log in right now."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if user is None:
        return Response(
            {"detail": "Invalid email or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Existing accounts without profiles are treated as verified.
    # New registrations explicitly create an unverified profile.
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"email_verified": True},
    )

    if not profile.email_verified:
        return Response(
            {
                "detail": "Please verify your email before logging in.",
                "email_verification_required": True,
                "email": user.email,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    login(request, user)

    return Response(
        {
            "message": "Login successful.",
            "user": UserSerializer(user).data,
        }
    )


# --------------------------------------------------
# Current authenticated user
# --------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    response = Response({
        "user": UserSerializer(request.user).data,
        "session": session_status(request._request),
    })
    response["Cache-Control"] = "no-store"
    return response


@csrf_protect
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_user_activity(request):
    """Only explicit, CSRF-protected user activity extends the session."""
    if not extend_user_activity(request._request):
        return Response({"detail": "Session expired."}, status=401)
    response = Response({"session": session_status(request._request)})
    response["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------
# Update user profile
# --------------------------------------------------

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    data = request.data
    errors = {}

    # Validate display name.
    name = data.get("name")

    if name is not None:
        if not isinstance(name, str) or not name.strip():
            errors["name"] = "Name is required."

        elif len(name.strip()) > 150:
            errors["name"] = (
                "Name must be 150 characters or fewer."
            )

    # Validate investment preferences.
    valid_choices = {
        "preferred_market": {
            "global",
            "us",
            "uk",
            "pakistan",
        },
        "risk_tolerance": {
            "conservative",
            "moderate",
            "aggressive",
        },
        "investment_horizon": {
            "short",
            "medium",
            "long",
        },
    }

    for field, allowed_values in valid_choices.items():
        value = data.get(field)

        if value is not None and value not in allowed_values:
            errors[field] = (
                f"Invalid value. Allowed values: "
                f"{', '.join(sorted(allowed_values))}."
            )

    # Validate preferred sectors.
    if "preferred_sectors" in data:
        sectors = data["preferred_sectors"]

        allowed_sectors = {
            "Technology",
            "Healthcare",
            "Finance",
            "Energy",
            "Consumer",
            "Industrials",
            "Real Estate",
            "Utilities",
            "Materials",
            "Communication Services",
        }

        if (
            not isinstance(sectors, list)
            or any(
                not isinstance(sector, str)
                or sector not in allowed_sectors
                for sector in sectors
            )
            or len(sectors) != len(set(sectors))
        ):
            errors["preferred_sectors"] = (
                "Choose valid sectors without duplicates."
            )

    if errors:
        return Response(
            errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Save only explicitly supplied fields.
    if name is not None:
        user.first_name = name.strip()
        user.save(update_fields=["first_name"])

    preference_fields = (
        "preferred_market",
        "risk_tolerance",
        "investment_horizon",
        "preferred_sectors",
    )

    supplied_preferences = {
        field: data[field]
        for field in preference_fields
        if field in data
    }

    if supplied_preferences:
        profile, _ = UserProfile.objects.get_or_create(
            user=user
        )

        for field, value in supplied_preferences.items():
            setattr(profile, field, value)

        profile.save(
            update_fields=list(supplied_preferences.keys())
        )

    return Response(
        {
            "message": "Profile updated successfully.",
            "user": UserSerializer(
                user,
                context={"request": request},
            ).data,
        }
    )


# --------------------------------------------------
# Upload profile picture
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_picture(request):
    uploaded_file = request.FILES.get("profile_picture")

    if not uploaded_file:
        return Response(
            {
                "profile_picture": (
                    "Please select an image to upload."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if uploaded_file.content_type not in allowed_types:
        return Response(
            {
                "profile_picture": (
                    "Only JPEG, PNG, and WebP images are allowed."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    max_size = 5 * 1024 * 1024

    if uploaded_file.size > max_size:
        return Response(
            {
                "profile_picture": (
                    "The image must be 5 MB or smaller."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify that the uploaded file is a real image.
    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(uploaded_file)
        image.verify()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return Response(
            {
                "profile_picture": (
                    "The uploaded file is not a valid image."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    uploaded_file.seek(0)

    if profile.profile_picture:
        profile.profile_picture.delete(save=False)

    profile.profile_picture = uploaded_file

    profile.save(
        update_fields=["profile_picture"]
    )

    return Response(
        {
            "message": "Profile picture uploaded successfully.",
            "user": UserSerializer(
                request.user,
                context={"request": request},
            ).data,
        }
    )


# --------------------------------------------------
# Logout
# --------------------------------------------------

@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    # Logout must work even when the session already expired or the user is
    # anonymous. Otherwise the UI can appear logged out while a cookie
    # remains valid. Django flushes the session and expires the cookie.
    logout(request._request)
    response = Response({"message": "Logged out successfully."})
    response["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------
# Email verification
# --------------------------------------------------

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
            raise ValueError("Invalid verification payload.")

        user = User.objects.get(
            pk=payload["user_id"],
            email__iexact=payload["email"],
        )

    except (
        signing.BadSignature,
        User.DoesNotExist,
        KeyError,
        TypeError,
        ValueError,
    ):
        return Response(
            {
                "detail": (
                    "This verification link is invalid or has expired."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"email_verified": False},
    )

    if profile.email_verified:
        return Response(
            {"message": "Your email is already verified."}
        )

    profile.email_verified = True

    profile.save(
        update_fields=["email_verified"]
    )

    return Response(
        {
            "message": (
                "Your email has been verified. You can now log in."
            )
        }
    )


# --------------------------------------------------
# Resend verification email
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([VerificationRateThrottle])
def resend_verification_email(request):
    email = str(
        request.data.get("email", "")
    ).strip().lower()

    user = User.objects.filter(
        email__iexact=email
    ).first()

    if user:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"email_verified": True},
        )

        if not profile.email_verified:
            try:
                send_verification_email(user)

            except Exception:
                logger.exception(
                    "Unable to resend verification email."
                )

    # Do not disclose whether an email exists.
    return Response(
        {
            "message": (
                "If an unverified account exists for that email, "
                "a verification email will be sent."
            )
        }
    )


# --------------------------------------------------
# Request password reset
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRateThrottle])
def request_password_reset(request):
    email = str(
        request.data.get("email", "")
    ).strip().lower()

    user = User.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()

    if user:
        try:
            send_password_reset_email(user)

        except Exception:
            logger.exception(
                "Unable to send password reset email."
            )

    # Prevent email enumeration.
    return Response(
        {
            "message": (
                "If an account exists for that email, "
                "a password reset link will be sent."
            )
        }
    )


# --------------------------------------------------
# Confirm password reset
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRateThrottle])
def confirm_password_reset(request):
    uidb64 = request.data.get("uid")
    token = request.data.get("token")
    password = request.data.get("password")
    password_confirm = request.data.get("password_confirm")

    if not all([
        uidb64,
        token,
        password,
        password_confirm,
    ]):
        return Response(
            {"detail": "All fields are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not all(
        isinstance(value, str)
        for value in (
            uidb64,
            token,
            password,
            password_confirm,
        )
    ):
        return Response(
            {"detail": "Invalid password reset data."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != password_confirm:
        return Response(
            {
                "password_confirm": (
                    "The passwords do not match."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = User.objects.get(
            pk=user_id,
            is_active=True,
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
    ):
        return Response(
            {
                "detail": (
                    "This password reset link is invalid or has expired."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(
        user,
        token,
    ):
        return Response(
            {
                "detail": (
                    "This password reset link is invalid or has expired."
                )
            },
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

    user.save(
        update_fields=["password"]
    )

    return Response(
        {
            "message": (
                "Your password has been reset successfully."
            )
        }
    )
