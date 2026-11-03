"""No-network Django regression checks for authenticated session boundaries."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from accounts.session_security import LAST_ACTIVITY_KEY, ISSUED_AT_KEY


@override_settings(
    MARKETPULSE_IDLE_TIMEOUT_SECONDS=1800,
    MARKETPULSE_ABSOLUTE_SESSION_SECONDS=43200,
    REST_FRAMEWORK={"DEFAULT_THROTTLE_CLASSES": [],
                    "DEFAULT_THROTTLE_RATES": {
                        "auth_login": "1000/hour",
                        "auth_password_reset": "1000/hour",
                        "auth_verification": "1000/hour",
                    }},
)
class VerifiedLoginSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.email = "security-review@example.com"
        cls.password = "A-long-strong-test-password-913!"
        cls.user = get_user_model().objects.create_user(
            username=cls.email,
            email=cls.email,
            password=cls.password,
        )
        UserProfile.objects.create(user=cls.user, email_verified=True)

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        response = self.client.get(reverse("auth-csrf"))
        self.csrf = response.json()["csrfToken"]

    def sign_in(self):
        return self.client.post(
            reverse("auth-login"),
            {"email": self.email, "password": self.password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )

    def test_login_is_csrf_protected_in_real_browser_configuration(self):
        no_csrf = Client(enforce_csrf_checks=True)
        response = no_csrf.post(
            reverse("auth-login"),
            {"email": self.email, "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_sets_server_activity_and_reports_expiry(self):
        response = self.sign_in()
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertIn(LAST_ACTIVITY_KEY, session)
        self.assertIn(ISSUED_AT_KEY, session)
        current = self.client.get(reverse("auth-current-user"))
        self.assertEqual(current.status_code, 200)
        self.assertTrue(current.json()["session"]["expires_at"])
        self.assertEqual(current["Cache-Control"], "no-store")

    def test_passive_requests_do_not_extend_idle_deadline(self):
        self.assertEqual(self.sign_in().status_code, 200)
        now = self.client.session[LAST_ACTIVITY_KEY]
        with patch("accounts.session_security.now_timestamp", return_value=now + 1700):
            for _ in range(4):
                current = self.client.get(reverse("auth-current-user"))
                self.assertEqual(current.status_code, 200)
                self.assertEqual(self.client.session[LAST_ACTIVITY_KEY], now)
        with patch("accounts.session_security.now_timestamp", return_value=now + 1801):
            expired = self.client.get(reverse("auth-current-user"))
            self.assertIn(expired.status_code, (401, 403))
        # A reload cannot restore the old cookie/session.
        refreshed = self.client.get(reverse("auth-current-user"))
        self.assertIn(refreshed.status_code, (401, 403))

    def test_explicit_activity_extends_idle_deadline(self):
        self.assertEqual(self.sign_in().status_code, 200)
        now = self.client.session[LAST_ACTIVITY_KEY]
        with patch("accounts.session_security.now_timestamp", return_value=now + 1600):
            active = self.client.post(
                reverse("auth-activity"), {},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
            )
            self.assertEqual(active.status_code, 200)
            self.assertGreater(self.client.session[LAST_ACTIVITY_KEY], now)
        with patch("accounts.session_security.now_timestamp", return_value=now + 1810):
            self.assertEqual(self.client.get(reverse("auth-current-user")).status_code, 200)

    def test_activity_requires_csrf(self):
        self.assertEqual(self.sign_in().status_code, 200)
        response = self.client.post(reverse("auth-activity"), {},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_logout_clears_session_and_refresh_cannot_reauthenticate(self):
        self.assertEqual(self.sign_in().status_code, 200)
        response = self.client.post(
            reverse("auth-logout"), {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.client.get(reverse("auth-current-user")).status_code, (401, 403))
        self.assertIn(self.client.get(reverse("auth-current-user")).status_code, (401, 403))

    def test_logout_without_csrf_never_claims_success(self):
        self.assertEqual(self.sign_in().status_code, 200)
        bad = self.client.post(
            reverse("auth-logout"), {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN="incorrect",
        )
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(self.client.get(reverse("auth-current-user")).status_code, 200)

    def test_logout_remains_idempotent_after_expiry(self):
        self.assertEqual(self.sign_in().status_code, 200)
        now = self.client.session[LAST_ACTIVITY_KEY]
        with patch("accounts.session_security.now_timestamp", return_value=now + 1801):
            self.assertIn(self.client.get(reverse("auth-current-user")).status_code, (401, 403))
        response = self.client.post(
            reverse("auth-logout"), {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 200)

    def test_absolute_cap_cannot_be_extended_by_activity(self):
        self.assertEqual(self.sign_in().status_code, 200)
        created = self.client.session[ISSUED_AT_KEY]
        with patch("accounts.session_security.now_timestamp", return_value=created + 43201):
            denied = self.client.get(reverse("auth-current-user"))
            self.assertIn(denied.status_code, (401, 403))
