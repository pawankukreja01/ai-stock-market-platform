from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase

from market_data.models import HistoricalPrice
from stocks.models import Stock


class BackfillStockHistoryTests(TestCase):
    def setUp(self):
        self.us = Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
        )
        Stock.objects.create(
            symbol="MSFT",
            company_name="Microsoft Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
        )
        self.uk = Stock.objects.create(
            symbol="AZN.L",
            company_name="AstraZeneca PLC",
            exchange="LSE",
            sector="Healthcare",
            industry="Pharmaceuticals",
        )

    def test_dry_run_does_not_download_or_write_prices(self):
        output = StringIO()

        with patch(
            "stocks.management.commands.backfill_stock_history.call_command"
        ) as ingest:
            call_command(
                "backfill_stock_history",
                dry_run=True,
                limit=10,
                stdout=output,
            )

        ingest.assert_not_called()
        self.assertEqual(HistoricalPrice.objects.count(), 0)
        self.assertIn("AAPL", output.getvalue())
        self.assertIn("AZN.L", output.getvalue())
        self.assertIn("Dry run only", output.getvalue())

    def test_market_and_resume_cursor_filter_targets(self):
        output = StringIO()

        call_command(
            "backfill_stock_history",
            dry_run=True,
            market="uk",
            after_symbol="AAPL",
            stdout=output,
        )

        self.assertIn("AZN.L", output.getvalue())
        self.assertNotIn("MSFT", output.getvalue())
        self.assertNotIn("AAPL |", output.getvalue())
        self.assertEqual(HistoricalPrice.objects.count(), 0)

    def test_retries_temporary_failure_and_stores_history(self):
        attempts = []

        def mock_ingestion(command_name, symbol, **kwargs):
            self.assertEqual(command_name, "ingest_stock_history")
            attempts.append(symbol)

            if len(attempts) == 1:
                raise CommandError("temporary provider failure")

            HistoricalPrice.objects.create(
                stock=self.us,
                date=date(2026, 10, 16),
                open_price=Decimal("100"),
                high_price=Decimal("105"),
                low_price=Decimal("99"),
                close_price=Decimal("104"),
                adjusted_close=Decimal("104"),
                volume=100000,
            )

        output = StringIO()

        with (
            patch(
                "stocks.management.commands.backfill_stock_history.call_command",
                side_effect=mock_ingestion,
            ),
            patch("stocks.management.commands.backfill_stock_history.time.sleep"),
        ):
            call_command(
                "backfill_stock_history",
                market="us",
                limit=1,
                retries=1,
                retry_delay=0,
                pause=0,
                stdout=output,
                stderr=output,
            )

        self.assertEqual(attempts, ["AAPL", "AAPL"])
        self.assertEqual(
            HistoricalPrice.objects.filter(stock=self.us).count(), 1
        )
        self.assertIn("Successful: 1", output.getvalue())

    def test_rejects_unsafe_batch_limit(self):
        with self.assertRaises(CommandError):
            call_command("backfill_stock_history", limit=1000)
