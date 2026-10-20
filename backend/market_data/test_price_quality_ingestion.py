from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.test import TestCase

from market_data.models import HistoricalPrice
from stocks.models import Stock


class PriceQualityIngestionTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
        )

    def make_history(self, rows):
        index = pd.to_datetime([row[0] for row in rows])
        data = [row[1:] for row in rows]
        return pd.DataFrame(
            data,
            index=index,
            columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"],
        )

    def run_ingestion(self, history):
        output = StringIO()
        with patch(
            "market_data.management.commands.ingest_stock_history.yf.Ticker"
        ) as ticker_factory:
            ticker_factory.return_value.history.return_value = history
            call_command(
                "ingest_stock_history",
                "AAPL",
                period="1y",
                stdout=output,
            )
            return output.getvalue(), ticker_factory

    def test_invalid_row_is_skipped_without_overwriting_existing_price(self):
        existing = HistoricalPrice.objects.create(
            stock=self.stock,
            date=date(2026, 10, 16),
            open_price=Decimal("100.0000"),
            high_price=Decimal("105.0000"),
            low_price=Decimal("99.0000"),
            close_price=Decimal("104.0000"),
            adjusted_close=Decimal("104.0000"),
            volume=100000,
        )

        history = self.make_history([
            # Invalid: high is lower than close.
            ("2026-10-16", 101, 102, 99, 104, 104, 120000),
            # Valid new record.
            ("2026-10-19", 105, 110, 104, 109, 109, 150000),
        ])

        output, ticker_factory = self.run_ingestion(history)

        existing.refresh_from_db()
        self.assertEqual(existing.close_price, Decimal("104.0000"))
        self.assertEqual(existing.volume, 100000)

        self.assertEqual(
            HistoricalPrice.objects.filter(stock=self.stock).count(), 2
        )
        self.assertTrue(
            HistoricalPrice.objects.filter(
                stock=self.stock,
                date=date(2026, 10, 19),
                close_price=Decimal("109.0000"),
            ).exists()
        )

        ticker_factory.return_value.history.assert_called_once_with(
            period="1y",
            auto_adjust=False,
            repair=True,
            timeout=30.0,
        )
        self.assertIn("1 records created", output)
        self.assertIn("0 records updated", output)
        self.assertIn("1 invalid records skipped", output)

    def test_missing_prices_are_skipped(self):
        history = self.make_history([
            ("2026-10-19", 105, 110, 104, float("nan"), 109, 150000),
        ])

        output, _ = self.run_ingestion(history)

        self.assertEqual(HistoricalPrice.objects.filter(stock=self.stock).count(), 0)
        self.assertIn("1 invalid records skipped", output)

    def test_valid_row_is_stored(self):
        history = self.make_history([
            ("2026-10-19", 105, 110, 104, 109, 109, 150000),
        ])

        output, _ = self.run_ingestion(history)

        saved = HistoricalPrice.objects.get(
            stock=self.stock,
            date=date(2026, 10, 19),
        )
        self.assertEqual(saved.close_price, Decimal("109.0000"))
        self.assertEqual(saved.volume, 150000)
        self.assertIn("1 records created", output)
        self.assertIn("0 invalid records skipped", output)
