"""Isolated preview archive and historical quote fallback regression tests."""
import gzip
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from market_data.preview_snapshot import (
    FIELDS, SCHEMA, SOURCE_DB, _valid_record,
    assert_database, export_snapshot, import_snapshot, preflight_snapshot,
)
from market_data.models import HistoricalPrice
from market_data.quote_views import LatestQuoteView
from stocks.models import Stock


def sample_stock(symbol="AAPL"):
    return {
        "type": "stock", "symbol": symbol,
        "fields": {
            "symbol": symbol, "company_name": "Apple Inc.", "exchange": "NASDAQ",
            "currency": "USD", "sector": "Technology",
            "industry": "Consumer Electronics", "is_active": True,
        },
    }


def sample_price(symbol="AAPL"):
    return {
        "type": "price", "symbol": symbol,
        "fields": {
            "date": "2024-01-03", "open_price": "100.0000",
            "high_price": "102.0000", "low_price": "99.0000",
            "close_price": "101.0000", "adjusted_close": "101.0000",
            "volume": 1234, "provider_currency": "USD",
            "storage_currency": "USD", "is_ohlc_valid": True,
            "is_volume_valid": True, "quality_flags": [],
        },
    }


class OfflinePreviewSnapshotTests(SimpleTestCase):
    def test_source_schema_and_input_allowlist_exclude_user_data(self):
        fields = set().union(*(set(names) for names in FIELDS.values()))
        for name in ("password", "email", "session_key", "profile", "token",
                     "portfolio", "secret", "username"):
            self.assertNotIn(name, fields)
        self.assertEqual(set(FIELDS), {"stock", "price", "fundamental", "news"})

    def test_rejects_extra_fields_or_user_owned_records(self):
        record = sample_price()
        record["fields"]["secret"] = "do-not-import"
        with self.assertRaisesRegex(ValueError, "Unexpected or missing"):
            _valid_record(record)
        with self.assertRaisesRegex(ValueError, "Disallowed"):
            _valid_record({"type": "user", "symbol": "AAPL", "fields": {}})

    def test_validates_complete_archive_before_any_writes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "offline.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as output:
                output.write(json.dumps({"schema": SCHEMA, "source": SOURCE_DB}) + "\n")
                output.write(json.dumps(sample_stock()) + "\n")
                output.write(json.dumps(sample_price()) + "\n")
            self.assertEqual(preflight_snapshot(path), {
                "stock": 1, "price": 1, "fundamental": 0, "news": 0,
            })
            with gzip.open(path, "at", encoding="utf-8") as output:
                output.write(json.dumps({"type": "user", "symbol": "AAPL", "fields": {}}) + "\n")
            with self.assertRaisesRegex(ValueError, "Invalid snapshot row"):
                preflight_snapshot(path)

    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_cannot_import_to_original_database(self):
        with self.assertRaisesRegex(CommandError, "Refusing market-data operation"):
            import_snapshot("/tmp/nonexistent-snapshot.jsonl.gz", dry_run=False)

    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_cannot_export_from_original_database(self):
        with self.assertRaisesRegex(CommandError, "Refusing market-data operation"):
            assert_database(SOURCE_DB)


class MarketSnapshotRoundTripTests(TestCase):
    def test_offline_export_import_is_idempotent_and_no_accounts_copied(self):
        stock = Stock.objects.create(
            symbol="AAPL", company_name="Apple Inc.",
            exchange="NASDAQ", currency="USD", is_active=True,
        )
        HistoricalPrice.objects.create(
            stock=stock, date=date(2024, 1, 3),
            open_price=Decimal("100"), high_price=Decimal("102"),
            low_price=Decimal("99"), close_price=Decimal("101"),
            adjusted_close=Decimal("101"), volume=1234,
            is_ohlc_valid=True, is_volume_valid=True,
            storage_currency="USD", provider_currency="USD",
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "archive.jsonl.gz"
            with patch("market_data.preview_snapshot.assert_database"):
                exported, export_counts = export_snapshot(path)
                self.assertEqual(exported, path)
                self.assertEqual(export_counts["stock"], 1)
                self.assertEqual(export_counts["price"], 1)
                counts, new_rows = import_snapshot(path)
                self.assertEqual(counts["price"], 1)
                self.assertEqual(new_rows["price"], 0)
                self.assertEqual(new_rows["stock"], 0)
                counts_again, repeat_rows = import_snapshot(path)
                self.assertEqual(repeat_rows["price"], 0)
                self.assertEqual(repeat_rows["stock"], 0)
            self.assertEqual(HistoricalPrice.objects.count(), 1)


class ArchivedQuoteTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="AAPL", company_name="Apple Inc.", exchange="NASDAQ",
            currency="USD", is_active=True,
        )

    def test_missing_archive_returns_clear_404(self):
        response = LatestQuoteView.as_view()(
            APIRequestFactory().get("/api/quotes/AAPL/"), symbol="AAPL",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["data_status"], "missing_stored_market_data")

    def test_archived_prices_are_displayed_but_never_called_live(self):
        for d, close in ((date(2024, 1, 2), "100"), (date(2024, 1, 3), "101")):
            HistoricalPrice.objects.create(
                stock=self.stock, date=d, open_price=Decimal(close),
                high_price=Decimal(close), low_price=Decimal(close),
                close_price=Decimal(close), adjusted_close=Decimal(close),
                volume=50, is_ohlc_valid=True, is_volume_valid=True,
                storage_currency="USD", provider_currency="USD",
            )
        response = LatestQuoteView.as_view()(
            APIRequestFactory().get("/api/quotes/AAPL/"), symbol="AAPL",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "stored_historical_archive")
        self.assertEqual(response.data["freshness_status"], "stale")
        self.assertIsNone(response.data["retrieved_at"])
        self.assertEqual(response.data["change_percent"], "1.00")
        self.assertIn("ARCHIVED DAILY CLOSE", response.data["data_note"])
