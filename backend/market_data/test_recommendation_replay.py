"""Read-only ranking replay protocol tests with synthetic future prices."""
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from market_data.recommendation_replay import (
    close_return_from_future_rows, summarize_periods, validate_replay_symbols,
)


class RecommendationReplayProtocolTests(SimpleTestCase):
    def test_first_future_close_entry_and_horizon_plus_one_exit(self):
        rows = [
            {"close_price": value, "is_ohlc_valid": True}
            for value in ("100", "102", "104", "106", "108", "110")
        ]
        self.assertAlmostEqual(
            close_return_from_future_rows(rows, horizon=5), .10,
        )
        self.assertAlmostEqual(
            close_return_from_future_rows(rows, horizon=1), .02,
        )

    def test_missing_future_row_never_forward_filled(self):
        rows = [{"close_price": "100", "is_ohlc_valid": True}]
        self.assertIsNone(close_return_from_future_rows(rows, horizon=1))
        rows.append({"close_price": None, "is_ohlc_valid": False})
        self.assertIsNone(close_return_from_future_rows(rows, horizon=1))

    def test_cohort_requires_unique_normalized_symbols(self):
        for items in ([], ["AAPL"], ["AAPL", "AAPL"],
                      ["AAPL", "aapl"], ["AAPL", "x$"]):
            with self.assertRaises(ValueError):
                validate_replay_symbols(items)
        self.assertEqual(validate_replay_symbols(["AAPL", "BP.L"]),
                         ["AAPL", "BP.L"])

    def test_missing_result_is_not_reported_as_accuracy(self):
        result = summarize_periods([
            {"status": "excluded"}, {"status": "excluded"},
        ])
        self.assertEqual(result["eligible_periods"], 0)
        self.assertIsNone(result["win_rate_against_equal_weight"])
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_win_rate_is_baseline_relative_not_profit_probability(self):
        result = summarize_periods([
            {"status": "evaluated", "relative_return": .02},
            {"status": "evaluated", "relative_return": -.01},
            {"status": "evaluated", "relative_return": .01},
            {"status": "excluded"},
        ])
        self.assertEqual(result["eligible_periods"], 3)
        self.assertEqual(result["excluded_periods"], 1)
        self.assertAlmostEqual(result["win_rate_against_equal_weight"], 2/3, places=4)

    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_original_db_rejected_before_loading_manifest(self):
        with TemporaryDirectory() as d:
            output = Path(d) / "should-not-exist.json"
            with self.assertRaisesRegex(CommandError, "Refusing to replay"):
                call_command(
                    "replay_recommendation_rankings",
                    cohort_file="/tmp/nonexistent-marketpulse-cohort.json",
                    start_date="2025-01-01",
                    end_date="2025-12-31",
                    output=str(output), stdout=StringIO(),
                )
            self.assertFalse(output.exists())
