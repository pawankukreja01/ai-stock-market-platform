
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from stocks.models import Stock

from .models import LatestQuote


class LatestQuoteAPITests(APITestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            currency="USD",
            is_active=True,
        )

        self.url = reverse(
            "latest-stock-quote",
            kwargs={"symbol": "AAPL"},
        )

    def create_quote(self, **overrides):
        values = {
            "stock": self.stock,
            "price": "250.000000",
            "previous_close": "245.000000",
            "volume": 1_000_000,
            "currency": "USD",
            "provider": "yfinance",
            "quote_type": "intraday_1m",
            "source_timestamp": timezone.now(),
        }

        values.update(overrides)

        return LatestQuote.objects.create(**values)

    def test_returns_404_when_no_quote_exists(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertIn("detail", response.data)

    def test_returns_stored_quote(self):
        self.create_quote()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["symbol"], "AAPL")
        self.assertEqual(response.data["company_name"], "Apple Inc.")
        self.assertEqual(response.data["price"], "250.000000")
        self.assertEqual(response.data["currency"], "USD")
        self.assertEqual(response.data["provider"], "yfinance")

    def test_calculates_price_change(self):
        self.create_quote()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["change"], "5.000000")
        self.assertEqual(response.data["change_percent"], "2.04")

    def test_recent_quote_has_recent_freshness_status(self):
        self.create_quote()

        response = self.client.get(self.url)

        self.assertEqual(response.data["freshness_status"], "recent")

    def test_old_quote_is_marked_stale(self):
        self.create_quote(
            source_timestamp=timezone.now() - timedelta(days=7)
        )

        response = self.client.get(self.url)

        self.assertEqual(response.data["freshness_status"], "stale")

    def test_daily_close_is_identified(self):
        self.create_quote(quote_type="daily_close")

        response = self.client.get(self.url)

        self.assertEqual(response.data["quote_type"], "daily_close")
        self.assertIn("daily closing price", response.data["data_note"])

    def test_unknown_stock_returns_404(self):
        response = self.client.get("/api/quotes/UNKNOWN/")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
