"""Integration tests: historical adjustments cannot silently overwrite records."""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from market_data.models import HistoricalPrice
from stocks.models import Stock


class HistoricalRevisionGuardTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="ABF.L", company_name="AB Foods", exchange="LSE",
            currency="GBP",
        )
        self.saved = HistoricalPrice.objects.create(
            stock=self.stock, date=date(2021, 11, 1),
            open_price=Decimal("18.0000"),
            high_price=Decimal("18.3000"),
            low_price=Decimal("17.9000"),
            close_price=Decimal("18.1250"),
            adjusted_close=Decimal("15.5576"),
            volume=1000,
            provider_currency="GBp",
            storage_currency="GBP",
        )

    def history(self):
        return pd.DataFrame({
            "Open": [1800.0, 1801.0],
            "High": [1830.0, 1840.0],
            "Low": [1790.0, 1785.0],
            "Close": [1812.5, 1818.0],
            "Adj Close": [1809.7595, 1815.2511],
            "Volume": [1000, 1200],
        }, index=pd.to_datetime(["2021-11-01", "2021-11-02"]))

    def run_command(self, **opts):
        with patch(
            "market_data.management.commands.ingest_stock_history.yf.Ticker"
        ) as factory:
            ticker = factory.return_value
            ticker.history.return_value = self.history()
            # GBPp currency metadata is explicitly provided by the mocked API.
            ticker.fast_info = {"currency": "GBp"}
            output = StringIO()
            call_command(
                "ingest_stock_history", "ABF.L",
                stdout=output, **opts
            )
            return output.getvalue()

    def test_large_adjustment_revisions_fail_closed_without_any_writes(self):
        with self.assertRaisesRegex(
            CommandError, "require review"
        ):
            self.run_command()
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.adjusted_close, Decimal("15.5576"))
        self.assertEqual(HistoricalPrice.objects.filter(stock=self.stock).count(), 1)
        self.assertEqual(self.stock.currency, "GBP")

    def test_dry_run_reports_revision_without_any_writes(self):
        output = self.run_command(dry_run=True)
        self.assertIn("CAUTION: 1 historical", output)
        self.assertIn("DRY RUN", output)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.adjusted_close, Decimal("15.5576"))
        self.assertEqual(HistoricalPrice.objects.filter(stock=self.stock).count(), 1)

    def test_explicit_authorization_applies_reviewed_revision(self):
        output = self.run_command(allow_adjustment_revisions=True)
        self.assertIn("1 records updated", output)
        self.assertIn("1 records created", output)
        self.saved.refresh_from_db()
        self.assertAlmostEqual(float(self.saved.adjusted_close), 18.0976, places=4)
        self.assertEqual(HistoricalPrice.objects.filter(stock=self.stock).count(), 2)

    def test_preflight_identifies_only_large_factor_revisions(self):
        from market_data.management.commands.ingest_stock_history import Command
        before = {date(2021, 11, 1): 0.85835, date(2021, 11, 2): 1.0}
        incoming = {date(2021, 11, 1): 0.998488, date(2021, 11, 2): 1.001}
        changes = Command._large_adjustment_revisions(before, incoming)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0][0], date(2021, 11, 1))

    def test_mixed_incoming_adjustment_conventions_flagged(self):
        from market_data.management.commands.ingest_stock_history import Command
        incoming = {
            date(2021, 10, 29): 0.998488,
            date(2021, 11, 1): 0.858353,
            date(2021, 11, 2): 0.858353,
        }
        jumps = Command._incoming_factor_jumps(incoming)
        self.assertEqual(len(jumps), 1)
        self.assertEqual(jumps[0][0], date(2021, 11, 1))

    def test_new_history_with_discontinuous_adjustments_is_rejected(self):
        self.saved.delete()
        with patch(
            "market_data.management.commands.ingest_stock_history.yf.Ticker"
        ) as factory:
            ticker = factory.return_value
            history = self.history()
            history.loc[history.index[0], "Adj Close"] = 1809.7595
            history.loc[history.index[1], "Adj Close"] = 1560.4856
            ticker.history.return_value = history
            with self.assertRaisesRegex(CommandError, "discontinuities"):
                call_command("ingest_stock_history", "ABF.L")
        self.assertFalse(
            HistoricalPrice.objects.filter(stock=self.stock).exists()
        )
