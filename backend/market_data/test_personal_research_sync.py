"""Tests for deliberately opt-in restored-test-DB research refresh."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from stocks.models import Stock
from market_data.management.commands.sync_personal_research import (
    verify_safe_database,
)


class ResearchSyncSafetyTests(TestCase):
    def setUp(self):
        Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            is_active=True,
        )

    def test_refuses_original_or_unset_database(self):
        for env, actual in (
            ("", "marketpulse_restored_test"),
            ("ai_stock_market", "ai_stock_market"),
            ("marketpulse_restored_test", "ai_stock_market"),
        ):
            with self.subTest(env=env, actual=actual):
                with self.assertRaisesRegex(CommandError, "requires DB_NAME"):
                    verify_safe_database(env, actual)

    def test_accepts_only_intended_restored_test_database(self):
        verify_safe_database(
            "marketpulse_restored_test",
            "marketpulse_restored_test",
        )

    @patch(
        "market_data.management.commands.sync_personal_research.verify_safe_database"
    )
    @patch(
        "market_data.management.commands.sync_personal_research.call_command"
    )
    def test_preview_never_calls_ingestion(self, ingest, safety_check):
        out = StringIO()
        call_command(
            "sync_personal_research",
            symbols=["AAPL"], stdout=out,
        )
        ingest.assert_not_called()
        safety_check.assert_called_once()
        self.assertIn("DRY RUN", out.getvalue())

    @patch(
        "market_data.management.commands.sync_personal_research.verify_safe_database"
    )
    @patch(
        "market_data.management.commands.sync_personal_research.call_command"
    )
    def test_explicit_execution_uses_incremental_history_by_default(
        self, ingest, safety_check,
    ):
        call_command(
            "sync_personal_research", symbols=["AAPL"], execute=True,
            stdout=StringIO(),
        )
        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.args[:2],
                         ("ingest_stock_history", "AAPL"))
        self.assertEqual(ingest.call_args.kwargs["period"], "1y")

    @patch(
        "market_data.management.commands.sync_personal_research.verify_safe_database"
    )
    @patch(
        "market_data.management.commands.sync_personal_research.call_command"
    )
    def test_news_and_sentiment_are_opt_in(self, ingest, safety_check):
        call_command(
            "sync_personal_research", symbols=["AAPL"], execute=True,
            include_news=True, include_sentiment=True,
            stdout=StringIO(),
        )
        self.assertEqual(
            [call.args[0] for call in ingest.call_args_list],
            ["ingest_stock_history", "ingest_stock_news", "analyze_news_sentiment"],
        )

    @patch(
        "market_data.management.commands.sync_personal_research.verify_safe_database"
    )
    def test_unknown_stock_causes_no_writes(self, safety_check):
        with self.assertRaisesRegex(CommandError, "Unknown or inactive"):
            call_command(
                "sync_personal_research", symbols=["UNKNOWN"],
                execute=True,
            )

    @patch(
        "market_data.management.commands.sync_personal_research.verify_safe_database"
    )
    def test_rejects_sentiment_without_news(self, safety_check):
        with self.assertRaisesRegex(CommandError, "requires --include-news"):
            call_command(
                "sync_personal_research", symbols=["AAPL"],
                include_sentiment=True, stdout=StringIO(),
            )
