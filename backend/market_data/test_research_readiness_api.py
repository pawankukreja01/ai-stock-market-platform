"""Readiness API access control, source transparency, and read-only behavior."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from market_data.models import HistoricalPrice
from market_data.research_readiness_views import parse_requested_symbols
from stocks.models import Stock


class ReadinessSymbolTests(TestCase):
    def test_symbols_are_normalized_and_deduplicated(self):
        self.assertEqual(
            parse_requested_symbols("aapl, abf.l, AAPL"),
            ["AAPL", "ABF.L"],
        )

    def test_unsafe_or_unbounded_symbols_are_rejected(self):
        for invalid in ("", "AAPL,,MSFT", "../etc/passwd", "AAPL;DROP", ",".join(
            f"T{i}" for i in range(21)
        )):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    parse_requested_symbols(invalid)


class ReadinessAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="health-reviewer",
            email="health-reviewer@example.com",
            password="test-password-not-production",
        )
        cls.stock = Stock.objects.create(
            symbol="ABF.L", company_name="Associated British Foods",
            exchange="LSE", is_active=True,
        )
        HistoricalPrice.objects.create(
            stock=cls.stock,
            date=date(2026, 11, 2),
            open_price=Decimal("18.0000"),
            high_price=Decimal("18.3000"),
            low_price=Decimal("17.9000"),
            close_price=Decimal("18.1250"),
            adjusted_close=Decimal("15.5576"),
            volume=100000,
        )

    def test_anonymous_request_is_denied(self):
        response = self.client.get(reverse("research-readiness"))
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_request_returns_read_only_stored_data(self):
        self.client.force_login(self.user)
        before = list(HistoricalPrice.objects.values_list(
            "pk", "close_price", "adjusted_close",
        ))
        with patch("yfinance.Ticker", side_effect=AssertionError(
            "Readiness endpoint must never contact Yahoo"
        )):
            response = self.client.get(
                reverse("research-readiness"), {"symbols": "abf.l"}
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["summary"]["stocks"], 1)
        self.assertEqual(payload["stocks"][0]["symbol"], "ABF.L")
        self.assertIn("missing_quote", payload["stocks"][0]["flags"])
        self.assertIn("not prediction accuracy", payload["note"])
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(
            list(HistoricalPrice.objects.values_list(
                "pk", "close_price", "adjusted_close",
            )), before
        )

    def test_missing_symbol_is_reported(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("research-readiness"), {"symbols": "MISSING"}
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_symbol_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("research-readiness"), {"symbols": "ABF.L,,NVDA"}
        )
        self.assertEqual(response.status_code, 400)

    def test_no_active_stocks_returns_empty_report(self):
        self.stock.is_active = False
        self.stock.save(update_fields=["is_active"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("research-readiness"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stocks"], [])
        self.assertEqual(response.json()["summary"]["stocks"], 0)
