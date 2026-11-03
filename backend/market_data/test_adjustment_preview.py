"""Read-only comparison of stored and Yahoo adjusted-close factors."""

from datetime import date
from io import StringIO
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from market_data.management.commands.preview_historical_adjustments import (
    compare_factors,
    factor_from_prices,
    find_factor_jumps,
    provider_adjustment_factors,
)


class HistoricalAdjustmentPreviewTests(SimpleTestCase):
    def test_ratios_are_currency_invariant_and_invalid_values_rejected(self):
        self.assertAlmostEqual(factor_from_prices(1812.5, 1555.7653), 0.858353, places=5)
        self.assertAlmostEqual(factor_from_prices(18.125, 15.557653), 0.858353)
        self.assertIsNone(factor_from_prices(0, 100))
        self.assertIsNone(factor_from_prices(1, float("nan")))

    def test_provider_rows_include_repair_count(self):
        dates = pd.date_range("2021-10-29", periods=3, freq="B", tz="Europe/London")
        frame = pd.DataFrame({
            "Close": [100.0, 102.0, 104.0],
            "Adj Close": [99.0, 101.0, 103.0],
            "Repaired?": [False, True, True],
        }, index=dates)
        factors, flagged = provider_adjustment_factors(frame)
        self.assertEqual(len(factors), 3)
        self.assertEqual(flagged, 2)
        self.assertAlmostEqual(factors[date(2021, 10, 29)], .99)

    def test_discontinuous_stored_factors_are_identified(self):
        before = date(2021, 10, 29)
        after = date(2021, 11, 1)
        stored = {before: .998488, after: .858353}
        provider_unrepaired = {before: .998488, after: .998488}
        provider_repaired = {before: .858353, after: .858353}
        jumps = find_factor_jumps(stored)
        self.assertEqual(jumps["count"], 1)
        self.assertEqual(jumps["examples"][0]["date"], "2021-11-01")
        self.assertEqual(
            compare_factors(stored, provider_unrepaired)["mismatch_count"], 1
        )
        self.assertEqual(
            compare_factors(stored, provider_repaired)["mismatch_count"], 1
        )
        self.assertEqual(stored[before], .998488)

    def test_identical_provider_and_stored_factors_have_no_mismatches(self):
        sample = {date(2021, 11, 1): .858353}
        report = compare_factors(sample, sample)
        self.assertEqual(report["shared_dates"], 1)
        self.assertEqual(report["mismatch_count"], 0)
        self.assertEqual(report["max_relative_difference_percent"], 0)

    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_guard_rejects_original_database_before_accessing_stocks(self):
        with self.assertRaisesRegex(CommandError, "requires explicit"):
            call_command(
                "preview_historical_adjustments",
                symbols=["ABF.L"],
                stdout=StringIO(),
            )

    @patch.dict("os.environ", {"DB_NAME": ""})
    def test_guard_rejects_missing_explicit_test_database(self):
        with self.assertRaisesRegex(CommandError, "requires explicit"):
            call_command(
                "preview_historical_adjustments",
                symbols=["ABF.L"],
                stdout=StringIO(),
            )

    def test_duplicate_provider_dates_rejected(self):
        frame = pd.DataFrame({
            "Close": [100.0, 101.0],
            "Adj Close": [90.0, 91.0],
        }, index=pd.to_datetime(["2021-11-01", "2021-11-01"]))
        with self.assertRaisesRegex(ValueError, "Duplicate provider date"):
            provider_adjustment_factors(frame)
