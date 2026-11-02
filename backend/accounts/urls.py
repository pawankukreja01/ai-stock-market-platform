from django.urls import path

from . import auth_views, views

urlpatterns = [
    path("csrf/", views.csrf_token, name="auth-csrf"),
    path("register/", auth_views.register, name="auth-register"),
    path("login/", auth_views.login_view, name="auth-login"),
    path("me/", views.current_user, name="auth-current-user"),
    path("logout/", views.logout_view, name="auth-logout"),
    path("profile/", views.update_profile, name="auth-update-profile"),
    path(
        "profile/picture/",
        views.upload_profile_picture,
        name="auth-upload-profile-picture",
    ),
    path("verify-email/", auth_views.verify_email, name="auth-verify-email"),
    path(
        "resend-verification/",
        auth_views.resend_verification_email,
        name="auth-resend-verification",
    ),
    path(
        "password-reset/",
        auth_views.request_password_reset,
        name="auth-password-reset",
    ),
    path(
        "password-reset/confirm/",
        auth_views.confirm_password_reset,
        name="auth-password-reset-confirm",
    ),
]
