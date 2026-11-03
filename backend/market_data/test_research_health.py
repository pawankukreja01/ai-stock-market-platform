"""Read-only personal market research health checks."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
import json
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from market_data.management.commands.audit_research_health import (
    research_health_status,
    regular_session_reference,
)
from market_data.models import Fundamental, HistoricalPrice, LatestQuote
from stocks.models import Stock


class ResearchHealthStatusTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
        self.defaults = {
            "now": self.now,
            "latest_price_date": date(2026, 11, 2),
            "price_count": 1000,
            "invalid_price_count": 0,
            "latest_quote_time": self.now - timedelta(minutes=5),
            "annual_count": 2,
            "quarterly_count": 0,
            "min_history": 300,
            "max_history_age_days": 7,
            "max_quote_age_minutes": 30,
        }

    def check(self, **changes):
        return research_health_status(**{**self.defaults, **changes})

    def test_valid_data_passes_even_if_quarterly_statement_missing(self):
        result = self.check()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["flags"], [])
        self.assertIn("quarterly_fundamentals_unavailable", result["availability_gaps"])

    def test_stale_provider_timestamp_does_not_appear_recent(self):
        result = self.check(latest_quote_time=self.now - timedelta(days=2))
        self.assertIn("stale_quote", result["flags"])
        self.assertEqual(result["status"], "attention")

    def test_invalid_and_future_data_are_reported(self):
        result = self.check(
            latest_price_date=date(2026, 11, 5),
            invalid_price_count=1,
            latest_quote_time=self.now + timedelta(minutes=10),
        )
        self.assertIn("future_price_date", result["flags"])
        self.assertIn("invalid_ohlc_rows", result["flags"])
        self.assertIn("invalid_quote_timestamp", result["flags"])

    def test_weekend_friday_close_does_not_age_as_live_quote(self):
        sunday = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)
        friday_close = datetime(2026, 11, 6, 21, 0, tzinfo=timezone.utc)
        result = self.check(
            now=sunday, exchange="NASDAQ", latest_quote_time=friday_close,
        )
        self.assertEqual(
            result["session_context"]["regular_session_state"],
            "outside_regular_hours",
        )
        self.assertNotIn("stale_quote", result["flags"])
        self.assertGreater(result["quote_source_age_minutes"], 30)

    def test_session_uses_new_york_dst_and_uk_clock(self):
        november = datetime(2026, 11, 3, 16, 47, tzinfo=timezone.utc)
        us, reference = regular_session_reference(
            now=november, exchange="NASDAQ"
        )
        self.assertEqual(us["market"], "US")
        self.assertEqual(us["regular_session_state"], "regular_hours")
        self.assertEqual(reference, november)

        uk, close = regular_session_reference(
            now=november, exchange="LSE"
        )
        self.assertEqual(uk["market"], "UK")
        self.assertEqual(uk["regular_session_state"], "outside_regular_hours")
        self.assertEqual(close.hour, 16)
        self.assertEqual(close.minute, 30)

    def test_preopen_uses_previous_close(self):
        monday = datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc)
        _, reference = regular_session_reference(
            now=monday, exchange="NASDAQ"
        )
        self.assertEqual(reference, datetime(
            2026, 11, 6, 21, 0, tzinfo=timezone.utc
        ))

    def test_missing_quote_is_not_assumed_live(self):
        result = self.check(latest_quote_time=None)
        self.assertIn("missing_quote", result["flags"])
        self.assertIsNone(result["quote_source_age_minutes"])


class ResearchHealthCommandTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="ABF.L", company_name="AB Foods",
            exchange="LSE", is_active=True,
        )
        HistoricalPrice.objects.create(
            stock=self.stock,
            date=date(2026, 11, 2),
            open_price=Decimal("100.00"),
            high_price=Decimal("101.00"),
            low_price=Decimal("99.00"),
            close_price=Decimal("100.00"),
            adjusted_close=Decimal("100.00"),
            volume=100,
        )
        Fundamental.objects.create(
            stock=self.stock, period_end=date(2026, 6, 30),
            period_type="annual",
        )

    def test_report_is_json_and_does_not_require_quote(self):
        out = StringIO()
        call_command(
            "audit_research_health", symbols=["ABF.L"],
            min_history=1, max_history_age_days=5000,
            stdout=out,
        )
        report = json.loads(out.getvalue())
        self.assertTrue(report["read_only"])
        self.assertEqual(report["summary"]["stocks"], 1)
        self.assertEqual(report["stocks"][0]["symbol"], "ABF.L")
        self.assertIn("missing_quote", report["stocks"][0]["flags"])
        self.assertEqual(report["summary"]["stocks_with_no_quarterly_statements"], 1)
        self.assertEqual(report["summary"]["stocks_with_no_news_articles"], 1)
        self.assertIn("news_articles_unavailable", report["stocks"][0]["availability_gaps"])

    def test_missing_selected_stock_is_an_error(self):
        with self.assertRaisesRegex(CommandError, "Unknown or inactive"):
            call_command("audit_research_health", symbols=["UNKNOWN"])

    def test_quote_is_measured_by_source_time(self):
        LatestQuote.objects.create(
            stock=self.stock, price=Decimal("100.00"),
            source_timestamp=datetime(2021, 11, 3, tzinfo=timezone.utc),
            quote_type="daily_close",
        )
        out = StringIO()
        call_command(
            "audit_research_health", symbols=["ABF.L"],
            min_history=1, max_history_age_days=5000,
            stdout=out,
        )
        report = json.loads(out.getvalue())
        self.assertIn("stale_quote", report["stocks"][0]["flags"])
