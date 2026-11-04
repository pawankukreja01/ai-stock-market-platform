from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class LivenessTests(SimpleTestCase):
    def test_public_probe_contains_no_infrastructure_secrets(self):
        response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "ok", "service": "marketpulse-api"
        })
        self.assertEqual(response["Cache-Control"], "no-store")


class DatabaseReadinessTests(TestCase):
    def test_ready_when_test_database_is_connected(self):
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready"})
        self.assertEqual(response["Cache-Control"], "no-store")

    @patch("config.health_views.connections")
    def test_returns_503_without_exposing_raw_db_error(self, connections):
        connections.__getitem__.side_effect = Exception(
            "secret-database-connection-string"
        )
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("secret-database", response.content.decode())
