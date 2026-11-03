from datetime import timedelta
from decimal import Decimal
from io import StringIO
import os
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from market_data.management.commands.monitor_market import (
    quote_is_fresh_for_alerts,
)
from stocks.models import Stock


class FreshnessTests(SimpleTestCase):
    def quote(self, price="200", age_minutes=1):
        return SimpleNamespace(
            price=Decimal(price),
            source_timestamp=timezone.now() - timedelta(minutes=age_minutes),
        )

    def test_fresh_stored_quote_accepted(self):
        self.assertTrue(quote_is_fresh_for_alerts(
            self.quote(), now=timezone.now(), max_age_minutes=30
        ))

    def test_stale_provider_timestamp_rejected_even_if_recently_fetched(self):
        self.assertFalse(quote_is_fresh_for_alerts(
            self.quote(age_minutes=90),
            now=timezone.now(), max_age_minutes=30,
        ))

    def test_future_dated_quote_rejected(self):
        self.assertFalse(quote_is_fresh_for_alerts(
            self.quote(age_minutes=-10),
            now=timezone.now(), max_age_minutes=30,
        ))

    def test_invalid_prices_rejected(self):
        self.assertFalse(quote_is_fresh_for_alerts(
            self.quote(price="0"), now=timezone.now(), max_age_minutes=30,
        ))


class OneCycleMonitorTests(TestCase):
    def setUp(self):
        # Tests use Django's isolated test DB, never the original database.
        env_patch = patch.dict(
            os.environ, {"DB_NAME": connection.settings_dict["NAME"]}
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.stock = Stock.objects.create(
            symbol="AAPL", company_name="Apple", exchange="NASDAQ",
            is_active=True,
        )

    def test_missing_explicit_db_name_is_rejected(self):
        with patch.dict(os.environ, {"DB_NAME": ""}):
            with self.assertRaisesRegex(CommandError, "explicit DB_NAME"):
                call_command("monitor_market", symbols=["AAPL"])

    def test_default_original_database_name_is_rejected(self):
        with patch(
            "market_data.management.commands.monitor_market.connection"
        ) as conn:
            conn.settings_dict = {"NAME": "ai_stock_market"}
            with patch.dict(os.environ, {"DB_NAME": "ai_stock_market"}):
                with self.assertRaisesRegex(CommandError, "protected"):
                    call_command("monitor_market", symbols=["AAPL"])

    @patch("market_data.management.commands.monitor_market.call_command")
    @patch("market_data.management.commands.monitor_market.fetch_latest_quote")
    def test_one_cycle_evaluates_only_fresh_quotes(self, fetch, evaluate):
        fetch.return_value = SimpleNamespace(
            price=Decimal("100"), currency="USD",
            source_timestamp=timezone.now(),
        )
        out = StringIO()
        call_command(
            "monitor_market", symbols=["AAPL"], stdout=out,
        )
        evaluate.assert_called_once()
        self.assertEqual(evaluate.call_args.kwargs["symbol"], "AAPL")
        self.assertTrue(evaluate.call_args.kwargs["price_only"])
        self.assertTrue(evaluate.call_args.kwargs["latest_prices"])
        self.assertIn("1 symbols evaluated", out.getvalue())

    @patch("market_data.management.commands.monitor_market.call_command")
    @patch("market_data.management.commands.monitor_market.fetch_latest_quote")
    def test_stale_quote_does_not_evaluate_alerts(self, fetch, evaluate):
        fetch.return_value = SimpleNamespace(
            price=Decimal("100"), currency="USD",
            source_timestamp=timezone.now() - timedelta(days=2),
        )
        out = StringIO()
        call_command("monitor_market", symbols=["AAPL"], stdout=out)
        evaluate.assert_not_called()
        self.assertIn("1 stale/invalid", out.getvalue())

    @patch("market_data.management.commands.monitor_market.call_command")
    @patch("market_data.management.commands.monitor_market.fetch_latest_quote")
    def test_rate_limit_stops_remaining_stocks_and_does_not_evaluate(
        self, fetch, evaluate,
    ):
        from market_data.quote_service import QuoteProviderRateLimited
        Stock.objects.create(
            symbol="MSFT", company_name="Microsoft", exchange="NASDAQ",
            is_active=True,
        )
        fetch.side_effect = QuoteProviderRateLimited("HTTP 429")
        with self.assertRaisesRegex(CommandError, "rate limited"):
            call_command(
                "monitor_market", symbols=["AAPL", "MSFT"],
                stdout=StringIO(), stderr=StringIO(),
            )
        fetch.assert_called_once()
        evaluate.assert_not_called()
