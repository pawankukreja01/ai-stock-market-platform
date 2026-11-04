"""No real Yahoo requests: provider rate limit and cached quote protections."""

from datetime import timedelta
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from market_data.models import LatestQuote
from market_data.provider_errors import is_provider_rate_limit, safe_provider_error
from market_data.quote_service import (
    QuoteProviderRateLimited, fetch_latest_quote,
)
from stocks.models import Stock


class ProviderErrorClassificationTests(SimpleTestCase):
    def test_explicit_429_messages_and_type_are_classified(self):
        self.assertTrue(is_provider_rate_limit(Exception("HTTP 429: Too Many Requests")))
        self.assertTrue(is_provider_rate_limit(Exception("status code: 429")))
        self.assertTrue(is_provider_rate_limit(QuoteProviderRateLimited("rate limit")))
        self.assertFalse(is_provider_rate_limit(ConnectionError("network unavailable")))
        self.assertFalse(is_provider_rate_limit(ValueError("No data found")))

    def test_safe_message_does_not_echo_provider_cookie_details(self):
        message = safe_provider_error(
            Exception("HTTP 429: Too Many Requests Cookie session-secret")
        )
        self.assertIn("rate limit", message)
        self.assertNotIn("session-secret", message)


class ProviderFailFastTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="AAPL", company_name="Apple", exchange="NASDAQ",
            currency="USD", is_active=True,
        )
        self.old = LatestQuote.objects.create(
            stock=self.stock, price=Decimal("200.000000"),
            source_timestamp=timezone.now() - timedelta(days=2),
            currency="USD", quote_type="daily_close",
        )

    @patch("market_data.quote_service.yf.Ticker")
    @patch("market_data.quote_service.get_provider_currency_details")
    def test_intraday_429_does_not_make_daily_request_or_overwrite_quote(
        self, metadata, factory,
    ):
        metadata.return_value = SimpleNamespace(storage_code="USD", raw_code="USD")
        ticker = factory.return_value
        ticker.history.side_effect = Exception("HTTP 429 Too Many Requests")
        with self.assertRaises(QuoteProviderRateLimited):
            fetch_latest_quote(self.stock)
        self.assertEqual(ticker.history.call_count, 1)
        self.old.refresh_from_db()
        self.assertEqual(self.old.price, Decimal("200.000000"))

    @patch("market_data.quote_service.yf.Ticker")
    @patch("market_data.quote_service.get_provider_currency_details")
    def test_currency_429_stops_before_history_request(
        self, metadata, factory,
    ):
        from market_data.currency_utils import CurrencyMetadataUnavailable
        metadata.side_effect = CurrencyMetadataUnavailable(
            "HTTP 429 Too Many Requests"
        )
        with self.assertRaises(QuoteProviderRateLimited):
            fetch_latest_quote(self.stock)
        factory.return_value.history.assert_not_called()

    @patch("market_data.management.commands.refresh_all_latest_quotes.fetch_latest_quote")
    def test_bulk_refresh_stops_after_first_rate_limit(self, fetch):
        Stock.objects.create(
            symbol="MSFT", company_name="Microsoft", exchange="NASDAQ",
            is_active=True,
        )
        fetch.side_effect = QuoteProviderRateLimited("HTTP 429")
        with self.assertRaises(CommandError):
            call_command(
                "refresh_all_latest_quotes",
                all_stocks=True, delay=0,
                stdout=StringIO(), stderr=StringIO(),
            )
        fetch.assert_called_once()
        self.old.refresh_from_db()
        self.assertEqual(self.old.price, Decimal("200.000000"))

    def test_currency_metadata_stops_after_first_429(self):
        from market_data.currency_utils import (
            CurrencyMetadataUnavailable,
            get_provider_currency_details,
        )

        class RefusingTicker:
            info_accessed = False

            @property
            def fast_info(self):
                raise RuntimeError("HTTP 429 Too Many Requests")

            @property
            def info(self):
                self.info_accessed = True
                return {"currency": "USD"}

        ticker = RefusingTicker()
        with self.assertRaises(CurrencyMetadataUnavailable):
            get_provider_currency_details(ticker, required=False)
        self.assertFalse(ticker.info_accessed)
