from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core import signing
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


EMAIL_VERIFICATION_SALT = "accounts.email-verification"


def send_verification_email(user):
    token = signing.dumps(
        {"user_id": user.pk, "email": user.email},
        salt=EMAIL_VERIFICATION_SALT,
    )

    base_url = settings.FRONTEND_BASE_URL.rstrip("/")
    verification_url = f"{base_url}/verify-email?{urlencode({'token': token})}"

    send_mail(
        subject="Verify your MarketPulse email",
        message=(
            f"Hello {user.first_name or user.get_username()},\n\n"
            "Thank you for registering with MarketPulse.\n"
            "Verify your email using this link:\n\n"
            f"{verification_url}\n\n"
            "This link expires after 24 hours.\n"
            "If you did not create this account, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )



def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    base_url = settings.FRONTEND_BASE_URL.rstrip("/")
    reset_url = f"{base_url}/reset-password/{uid}/{token}"

    send_mail(
        subject="Reset your MarketPulse password",
        message=(
            f"Hello {user.first_name or user.get_username()},\n\n"
            "A password reset was requested for your account.\n"
            "Choose a new password using this link:\n\n"
            f"{reset_url}\n\n"
            "This link expires after one hour.\n"
            "If you did not request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    # Return the URL for local development convenience.
    return reset_url
