
from urllib.parse import urlparse, parse_qs
from django.core.signing import TimestampSigner

from django.contrib.auth import get_user_model
from django.core import mail
from django.core import signing
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from rest_framework.test import APIClient

from .email_utils import EMAIL_VERIFICATION_SALT
from .models import UserProfile


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://localhost:5173",
    EMAIL_VERIFICATION_MAX_AGE=60 * 60 * 24,
    PASSWORD_RESET_TIMEOUT=60 * 60,
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {
            "auth_verification": "5/hour",
            "auth_password_reset": "5/hour",
        },
    },
)
class AuthenticationTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.email = "testuser@example.com"
        self.password = "StrongTestPassword!928"

        self.user = User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            first_name="Test User",
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            email_verified=False,
        )

    def register_user(self):
        return self.client.post(
            reverse("auth-register"),
            {
                "name": "New User",
                "email": "newuser@example.com",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
        )

    def get_verification_token(self, email):
        user = User.objects.get(email=email)

        return signing.dumps(
            {
                "user_id": user.pk,
                "email": user.email,
            },
            salt=EMAIL_VERIFICATION_SALT,
        )

    def test_registration_creates_unverified_account(self):
        response = self.register_user()

        self.assertEqual(response.status_code, 201)

        user = User.objects.get(email="newuser@example.com")

        self.assertFalse(user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_sends_verification_link(self):
        response = self.register_user()

        self.assertEqual(response.status_code, 201)

        email = mail.outbox[0]

        self.assertIn("Verify your MarketPulse email", email.subject)
        self.assertIn("/verify-email?token=", email.body)

    def test_unverified_user_cannot_login(self):
        response = self.client.post(
            reverse("auth-login"),
            {
                "email": self.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            response.data["email_verification_required"]
        )

    def test_valid_verification_token_verifies_email(self):
        token = self.get_verification_token(self.email)

        response = self.client.post(
            reverse("auth-verify-email"),
            {"token": token},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.profile.refresh_from_db()

        self.assertTrue(self.profile.email_verified)

    def test_invalid_verification_token_is_rejected(self):
        response = self.client.post(
            reverse("auth-verify-email"),
            {"token": "invalid-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


    def test_expired_verification_token_is_rejected(self):
        signer = TimestampSigner(
            salt=EMAIL_VERIFICATION_SALT
        )

        token = signer.sign_object(
            {
                "user_id": self.user.pk,
                "email": self.user.email,
            }
        )

        with override_settings(EMAIL_VERIFICATION_MAX_AGE=0):
            response = self.client.post(
                reverse("auth-verify-email"),
                {"token": token},
                format="json",
            )

        self.assertEqual(response.status_code, 400)


    def test_verified_user_can_login(self):
        self.profile.email_verified = True
        self.profile.save(update_fields=["email_verified"])

        response = self.client.post(
            reverse("auth-login"),
            {
                "email": self.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.data)

    def test_resend_verification_email(self):
        response = self.client.post(
            reverse("auth-resend-verification"),
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_request_sends_email(self):
        self.profile.email_verified = True
        self.profile.save(update_fields=["email_verified"])

        response = self.client.post(
            reverse("auth-password-reset"),
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_does_not_disclose_unknown_email(self):
        response = self.client.post(
            reverse("auth-password-reset"),
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = self._get_password_reset_token()

        new_password = "AnotherStrongPassword!739"

        response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": token,
                "password": new_password,
                "password_confirm": new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(new_password)
        )

    def test_password_reset_token_cannot_be_reused(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = self._get_password_reset_token()

        new_password = "AnotherStrongPassword!739"

        payload = {
            "uid": uid,
            "token": token,
            "password": new_password,
            "password_confirm": new_password,
        }

        first_response = self.client.post(
            reverse("auth-password-reset-confirm"),
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            reverse("auth-password-reset-confirm"),
            payload,
            format="json",
        )

        self.assertEqual(second_response.status_code, 400)

    def _get_password_reset_token(self):
        from django.contrib.auth.tokens import default_token_generator

        return default_token_generator.make_token(self.user)
